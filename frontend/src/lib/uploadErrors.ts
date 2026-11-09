type DropzoneError = { code: string };

const REJECTION_MESSAGES: Record<string, string> = {
  "file-invalid-type": "Choose a PDF, JPG, PNG, or WEBP file.",
  "file-too-large": "This file is larger than the 10 MB limit.",
  "too-many-files": "You can upload fewer files at a time on your current plan.",
};

export function describeUploadRejection(errors: readonly DropzoneError[]): string {
  return errors
    .map(({ code }) => REJECTION_MESSAGES[code] ?? "This file could not be added. Check the file and try again.")
    .join(" ");
}
