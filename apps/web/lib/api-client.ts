import {
  type AnalysisFormValues,
  type PerceptionRun,
  type ProblemDetails,
  perceptionRunSchema,
  problemDetailsSchema,
} from "./schemas";

export class ApiProblemError extends Error {
  problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail);
    this.name = "ApiProblemError";
    this.problem = problem;
  }
}

export async function createPerceptionRun(
  values: AnalysisFormValues,
  images: File[],
): Promise<PerceptionRun> {
  if (process.env.NEXT_PUBLIC_USE_FIXTURES === "true") {
    await new Promise((resolve) => setTimeout(resolve, 250));
    const response = await fetch("/fixtures/mock-run.json");
    return perceptionRunSchema.parse(await response.json());
  }

  const formData = new FormData();
  images.forEach((image) => formData.append("images", image));
  Object.entries(values).forEach(([key, value]) => {
    if (value) {
      formData.append(key, value);
    }
  });

  const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  const response = await fetch(`${baseUrl}/api/v1/perception-runs`, {
    method: "POST",
    body: formData,
  });
  const payload = await response.json();
  if (!response.ok) {
    const parsed = problemDetailsSchema.safeParse(payload);
    if (parsed.success) {
      throw new ApiProblemError(parsed.data);
    }
    throw new Error("Analysis request failed.");
  }
  return perceptionRunSchema.parse(payload);
}
