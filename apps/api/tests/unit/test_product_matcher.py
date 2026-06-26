from datetime import UTC, datetime

from marketing_agent.domain.models.evidence import EvidenceRecord, EvidenceSource
from marketing_agent.domain.models.marketplace import (
    NormalizedMarketplaceListing,
    ProductCondition,
    ProductIdentity,
    ProductMatchStatus,
    ProductRelationship,
    RankSignal,
)
from marketing_agent.domain.services.product_matcher import (
    decimal_or_none,
    match_listing,
    normalize_brand,
    normalize_identifier,
    normalize_model_number,
    normalize_text,
    parse_condition,
    parse_package,
)


def test_text_and_model_normalization_preserve_meaningful_digits() -> None:
    assert normalize_text("Sony WH-1000XM5™  Headphones") == "sony wh-1000xm5 headphones"
    assert normalize_model_number("WH 1000 XM5") == "WH1000XM5"
    assert normalize_model_number("WH-1000XM4") != normalize_model_number("WH-1000XM5")


def test_identifier_and_brand_normalization() -> None:
    assert normalize_identifier("036000291452", "upc") == "036000291452"
    assert normalize_identifier("036000291453", "upc") is None
    assert normalize_brand("Hewlett Packard") == "hp"
    assert normalize_brand("HP") == "hp"


def test_package_and_condition_parsing() -> None:
    assert parse_package("Pack of 2")[0] == 2
    assert parse_package("3 × 12 oz") == (3, 12.0, "oz")
    assert parse_package("500 mL") == (None, 500.0, "ml")
    assert parse_condition("Certified refurbished") == ProductCondition.REFURBISHED
    assert parse_condition("Open box") == ProductCondition.OPEN_BOX
    assert parse_condition("For parts only") == ProductCondition.FOR_PARTS


def test_landed_price_is_calculated_from_components() -> None:
    listing = _listing(
        title="Sony WH-1000XM5 Headphones",
        item_price=300,
        shipping_price=10,
        mandatory_fees=5,
        discount=20,
    )
    assert listing.landed_price == decimal_or_none(295)


def test_model_conflict_rejects_even_when_title_is_similar() -> None:
    result = match_listing(
        _identity(model_number="WH-1000XM5"),
        _listing(title="Sony WH-1000XM4 Wireless Headphones", model_number="WH-1000XM4"),
    )
    assert result.status == ProductMatchStatus.REJECTED
    assert [conflict.code for conflict in result.conflicts] == ["MODEL_NUMBER_MISMATCH"]
    assert result.eligible_for_price_aggregation is False


def test_brand_alias_can_match_exact_product() -> None:
    result = match_listing(
        _identity(
            brand="Hewlett Packard",
            product_name="HP LaserJet Pro M404dn Printer",
            model_number="M404dn",
        ),
        _listing(
            title="HP LaserJet Pro M404dn Printer",
            brand="HP",
            model_number="M404dn",
        ),
    )
    assert result.status == ProductMatchStatus.EXACT_MATCH
    assert result.eligible_for_price_aggregation is True


def test_compatible_xbox_phrase_does_not_count_as_official_brand() -> None:
    result = match_listing(
        _identity(
            brand="Xbox",
            manufacturer="Microsoft",
            product_name="Microsoft Xbox Wireless Controller",
            product_type="controller",
            official_product_line="Xbox Wireless Controller",
            allowed_brand_aliases=["Xbox", "Microsoft Xbox"],
            allowed_manufacturer_aliases=["Microsoft", "Microsoft Corporation"],
            official_name_patterns=[
                "Xbox Wireless Controller",
                "Xbox Elite Wireless Controller Series 2",
            ],
            target_is_official_product=True,
        ),
        _listing(title="JAYSUING Wireless Controller for Microsoft Xbox Series X/S"),
    )

    assert result.relationship == ProductRelationship.GENERIC_COMPATIBLE_ALTERNATIVE
    assert result.status == ProductMatchStatus.REJECTED
    assert result.eligible_for_price_aggregation is False
    assert "EXPECTED_BRAND_ONLY_IN_COMPATIBILITY_PHRASE" in result.reason_codes
    assert result.official_name_verification is not None
    assert result.official_name_verification.detected_listing_brand == "JAYSUING"


def test_known_licensed_third_party_xbox_controller_is_separated() -> None:
    result = match_listing(
        _identity(
            brand="Xbox",
            manufacturer="Microsoft",
            product_name="Microsoft Xbox Wireless Controller",
            product_type="controller",
            official_product_line="Xbox Wireless Controller",
            allowed_brand_aliases=["Xbox", "Microsoft Xbox"],
            allowed_manufacturer_aliases=["Microsoft", "Microsoft Corporation"],
            official_name_patterns=[
                "Xbox Wireless Controller",
                "Xbox Elite Wireless Controller Series 2",
            ],
            target_is_official_product=True,
        ),
        _listing(title="PowerA Wireless Controller for Xbox Series X|S"),
    )

    assert result.relationship == ProductRelationship.LICENSED_THIRD_PARTY_ALTERNATIVE
    assert result.status == ProductMatchStatus.REJECTED
    assert result.aggregation_group == "licensed_alternative"
    assert result.eligible_for_price_aggregation is False


def test_official_xbox_variant_is_not_mixed_into_exact_price_aggregation() -> None:
    result = match_listing(
        _identity(
            brand="Xbox",
            manufacturer="Microsoft",
            product_name="Microsoft Xbox Wireless Controller",
            product_type="controller",
            official_product_line="Xbox Wireless Controller",
            allowed_brand_aliases=["Xbox", "Microsoft Xbox"],
            allowed_manufacturer_aliases=["Microsoft", "Microsoft Corporation"],
            official_name_patterns=[
                "Xbox Wireless Controller",
                "Xbox Elite Wireless Controller Series 2",
            ],
            target_is_official_product=True,
        ),
        _listing(title="Xbox Wireless Controller - Robot White"),
    )

    assert result.relationship == ProductRelationship.OFFICIAL_SAME_PRODUCT_FAMILY
    assert result.aggregation_group == "official_variant"
    assert result.eligible_for_price_aggregation is False


def test_accessory_listing_is_rejected_for_main_product() -> None:
    result = match_listing(
        _identity(product_name="Canon EOS R50 Camera", product_type="camera"),
        _listing(title="Protective case for Canon EOS R50 Camera"),
    )
    assert result.status == ProductMatchStatus.REJECTED
    assert result.conflicts[0].code == "ACCESSORY_MISMATCH"


def test_multipack_is_alternate_package_not_primary_price() -> None:
    result = match_listing(
        _identity(product_name="Portable Rechargeable Desk Lamp"),
        _listing(title="Portable Rechargeable Desk Lamp Pack of 2", pack_quantity=2),
    )
    assert result.status == ProductMatchStatus.UNCERTAIN
    assert result.aggregation_group == "alternate_package"
    assert result.eligible_for_price_aggregation is False


def test_used_or_refurbished_condition_is_separated() -> None:
    result = match_listing(
        _identity(product_name="Apple iPhone 15 Pro 256GB"),
        _listing(
            title="Apple iPhone 15 Pro 256GB refurbished",
            condition=ProductCondition.REFURBISHED,
        ),
    )
    assert result.status == ProductMatchStatus.REJECTED
    assert result.aggregation_group == "alternate_condition"
    assert result.conflicts[0].code == "CONDITION_MISMATCH"


def test_variant_mismatch_requires_review_and_is_not_primary() -> None:
    result = match_listing(
        _identity(product_name="Apple iPhone 15 Pro 256GB", variant="256gb"),
        _listing(title="Apple iPhone 15 Pro 128GB", variant="128gb"),
    )
    assert result.status == ProductMatchStatus.UNCERTAIN
    assert result.aggregation_group == "alternate_variant"
    assert result.eligible_for_price_aggregation is False


def test_edition_variant_mismatch_requires_review() -> None:
    result = match_listing(
        _identity(product_name="Apple iPhone 15 Pro 256GB", variant="256gb"),
        _listing(title="Apple iPhone 15 256GB", variant="256gb"),
    )
    assert result.status == ProductMatchStatus.UNCERTAIN
    assert result.aggregation_group == "alternate_variant"
    assert result.conflicts[0].code == "VARIANT_MISMATCH"


def _identity(
    *,
    brand: str | None = None,
    manufacturer: str | None = None,
    product_name: str = "Sony WH-1000XM5 Wireless Headphones",
    product_type: str = "headphones",
    model_number: str | None = None,
    variant: str | None = None,
    official_product_line: str | None = None,
    allowed_brand_aliases: list[str] | None = None,
    allowed_manufacturer_aliases: list[str] | None = None,
    official_name_patterns: list[str] | None = None,
    target_is_official_product: bool | None = None,
) -> ProductIdentity:
    manufacturer_value = manufacturer or brand
    evidence = [
        EvidenceRecord(
            id="ev-test-identity",
            source=EvidenceSource.MODEL_INFERENCE,
            source_reference="test",
            observation="Test identity",
            confidence=1.0,
        )
    ]
    return ProductIdentity(
        brand=brand,
        manufacturer=manufacturer_value,
        product_name=product_name,
        normalized_product_name=normalize_text(product_name),
        official_product_line=official_product_line,
        product_type=product_type,
        category=product_type,
        model_number=model_number,
        variant=variant,
        expected_condition=ProductCondition.NEW,
        normalized_title=normalize_text(
            " ".join(part for part in (manufacturer_value, brand, product_name) if part)
        ),
        allowed_brand_aliases=allowed_brand_aliases or ([brand] if brand else []),
        allowed_manufacturer_aliases=allowed_manufacturer_aliases
        or ([manufacturer_value] if manufacturer_value else []),
        official_name_patterns=official_name_patterns
        or ([official_product_line] if official_product_line else []),
        target_is_official_product=(
            target_is_official_product
            if target_is_official_product is not None
            else bool(brand and normalize_text(brand) in _tokens_for_test(product_name))
        ),
        aliases=[product_name],
        excluded_terms=[],
        source_evidence=evidence,
    )


def _listing(
    *,
    title: str,
    brand: str | None = None,
    model_number: str | None = None,
    condition: ProductCondition = ProductCondition.NEW,
    pack_quantity: int | None = None,
    variant: str | None = None,
    item_price: float = 299.99,
    shipping_price: float | None = None,
    mandatory_fees: float | None = None,
    discount: float | None = None,
) -> NormalizedMarketplaceListing:
    return NormalizedMarketplaceListing(
        provider="test",
        platform="Amazon",
        listing_id=title,
        title=title,
        normalized_title=normalize_text(title),
        brand=brand,
        provider_brand=brand,
        model_number=model_number,
        variant=variant,
        condition=condition,
        pack_quantity=pack_quantity,
        item_price=decimal_or_none(item_price),
        shipping_price=decimal_or_none(shipping_price),
        mandatory_fees=decimal_or_none(mandatory_fees),
        discount=decimal_or_none(discount),
        currency="USD",
        seller_name="Amazon",
        raw_rank_signals=[RankSignal(name="position", value=1.0, source="test")],
        observed_at=datetime.now(UTC),
    )


def _tokens_for_test(value: str) -> set[str]:
    return set(normalize_text(value).split())
