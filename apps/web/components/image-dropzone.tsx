"use client";

import { Upload, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_IMAGES = 5;

type Preview = {
  file: File;
  url: string;
};

type Props = {
  files: File[];
  onChange: (files: File[]) => void;
};

export function ImageDropzone({ files, onChange }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const previews = useMemo<Preview[]>(
    () => files.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [files],
  );

  useEffect(() => {
    return () =>
      previews.forEach((preview) => URL.revokeObjectURL(preview.url));
  }, [previews]);

  function addFiles(nextFiles: FileList | File[]) {
    const incoming = Array.from(nextFiles);
    const invalid = incoming.find(
      (file) => !ACCEPTED_TYPES.includes(file.type),
    );
    if (invalid) {
      setError("Use JPG, PNG, or WebP images.");
      return;
    }
    const merged = [...files, ...incoming];
    if (merged.length > MAX_IMAGES) {
      setError("Upload one to five images.");
      return;
    }
    setError(null);
    onChange(merged);
  }

  function removeFile(index: number) {
    setError(null);
    onChange(files.filter((_, current) => current !== index));
  }

  return (
    <div className="min-w-0">
      <label
        className="block text-sm font-medium text-gray-900"
        htmlFor="product-images"
      >
        Product images
      </label>
      <div
        className={`mt-2 flex min-h-36 min-w-0 flex-col items-center justify-center rounded border border-dashed px-4 py-6 text-center ${
          isDragging
            ? "border-accent-600 bg-accent-50"
            : "border-gray-300 bg-white"
        }`}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          addFiles(event.dataTransfer.files);
        }}
      >
        <Upload aria-hidden="true" className="h-6 w-6 text-gray-500" />
        <p className="mt-2 text-sm text-gray-700">
          Drag images here or choose files.
        </p>
        <input
          id="product-images"
          aria-describedby={error ? "image-error" : undefined}
          className="mt-3 block w-full max-w-full text-sm text-gray-700 file:mr-3 file:rounded file:border-0 file:bg-accent-600 file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-accent-700 sm:max-w-sm"
          type="file"
          accept={ACCEPTED_TYPES.join(",")}
          multiple
          onChange={(event) => {
            if (event.target.files) {
              addFiles(event.target.files);
            }
            event.currentTarget.value = "";
          }}
        />
      </div>
      {error ? (
        <p className="mt-2 text-sm text-red-700" id="image-error" role="alert">
          {error}
        </p>
      ) : null}
      {previews.length > 0 ? (
        <ul className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-5">
          {previews.map((preview, index) => (
            <li
              key={`${preview.file.name}-${index}`}
              className="min-w-0 rounded border border-gray-200 p-2"
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- object URLs are local upload previews. */}
              <img
                alt=""
                className="aspect-square w-full rounded object-cover"
                src={preview.url}
              />
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="min-w-0 truncate text-xs text-gray-700">
                  {preview.file.name}
                </span>
                <button
                  aria-label={`Remove ${preview.file.name}`}
                  className="rounded p-1 text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                  type="button"
                  onClick={() => removeFile(index)}
                >
                  <X aria-hidden="true" className="h-4 w-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
