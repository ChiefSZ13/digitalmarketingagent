"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { RotateCcw, Send } from "lucide-react";
import { useState } from "react";
import { type UseFormRegisterReturn, useForm } from "react-hook-form";
import { type AnalysisFormValues, analysisFormSchema } from "@/lib/schemas";
import { ImageDropzone } from "./image-dropzone";

type Props = {
  isSubmitting: boolean;
  onSubmit: (values: AnalysisFormValues, files: File[]) => void;
  onReset: () => void;
};

export function ProductAnalysisForm({
  isSubmitting,
  onSubmit,
  onReset,
}: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [imageError, setImageError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AnalysisFormValues>({
    resolver: zodResolver(analysisFormSchema),
    defaultValues: {
      description: "",
      brand: "",
      market: "US",
      language: "en-US",
      category_hint: "",
      target_audience_hint: "",
    },
  });

  function resetForm() {
    setFiles([]);
    setImageError(null);
    reset();
    onReset();
  }

  return (
    <form
      className="min-w-0 space-y-5 rounded border border-gray-200 bg-white p-4 sm:p-5"
      onSubmit={handleSubmit((values) => {
        if (files.length === 0) {
          setImageError("At least one image is required.");
          return;
        }
        setImageError(null);
        onSubmit(values, files);
      })}
    >
      <ImageDropzone files={files} onChange={setFiles} />
      {imageError ? (
        <p className="text-sm text-red-700" role="alert">
          {imageError}
        </p>
      ) : null}

      <div>
        <label
          className="block text-sm font-medium text-gray-900"
          htmlFor="description"
        >
          Product description
        </label>
        <textarea
          id="description"
          className="mt-2 min-h-28 w-full rounded border border-gray-300 px-3 py-2 text-sm"
          aria-invalid={Boolean(errors.description)}
          aria-describedby={
            errors.description ? "description-error" : undefined
          }
          {...register("description")}
        />
        {errors.description ? (
          <p
            className="mt-2 text-sm text-red-700"
            id="description-error"
            role="alert"
          >
            {errors.description.message}
          </p>
        ) : null}
      </div>

      <div className="grid min-w-0 gap-4 sm:grid-cols-2">
        <TextInput label="Brand" id="brand" register={register("brand")} />
        <TextInput label="Market" id="market" register={register("market")} />
        <TextInput
          label="Language"
          id="language"
          register={register("language")}
        />
        <TextInput
          label="Category hint"
          id="category_hint"
          register={register("category_hint")}
        />
        <div className="sm:col-span-2">
          <TextInput
            label="Target audience hint"
            id="target_audience_hint"
            register={register("target_audience_hint")}
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          className="inline-flex items-center gap-2 rounded bg-accent-600 px-4 py-2 text-sm font-medium text-white hover:bg-accent-700 disabled:cursor-not-allowed disabled:opacity-60"
          type="submit"
          disabled={isSubmitting}
        >
          <Send aria-hidden="true" className="h-4 w-4" />
          Analyze
        </button>
        <button
          className="inline-flex items-center gap-2 rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50"
          type="button"
          onClick={resetForm}
        >
          <RotateCcw aria-hidden="true" className="h-4 w-4" />
          Reset
        </button>
      </div>
    </form>
  );
}

type TextInputProps = {
  label: string;
  id: keyof AnalysisFormValues;
  register: UseFormRegisterReturn;
};

function TextInput({ label, id, register }: TextInputProps) {
  return (
    <div className="min-w-0">
      <label className="block text-sm font-medium text-gray-900" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        className="mt-2 min-w-0 w-full rounded border border-gray-300 px-3 py-2 text-sm"
        type="text"
        {...register}
      />
    </div>
  );
}
