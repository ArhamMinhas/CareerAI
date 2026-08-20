"use client";

import { useRef, useState, type DragEvent } from "react";
import { Loader2, Upload } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ResumeSummary } from "@/lib/types/resume";

const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

export function ResumeUpload({ onUploaded }: { onUploaded: (resume: ResumeSummary) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    if (!ACCEPTED_TYPES.includes(file.type) && !/\.(pdf|docx)$/i.test(file.name)) {
      setError("Only PDF and DOCX files are supported.");
      return;
    }
    setError(null);
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const resume = await apiFetch<ResumeSummary>("/api/v1/resumes/upload", {
        method: "POST",
        body: formData,
      });
      onUploaded(resume);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) void handleFile(file);
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed px-6 py-12 text-center transition-all duration-200 ease-out",
          dragging
            ? "border-primary bg-primary/5"
            : "border-border-strong hover:border-primary/40 hover:bg-surface"
        )}
      >
        {uploading ? (
          <Loader2 className="size-8 animate-spin text-primary" strokeWidth={1.5} />
        ) : (
          <Upload className="size-8 text-muted-foreground" strokeWidth={1.5} />
        )}
        <div>
          <p className="text-sm font-medium text-foreground">
            {uploading ? "Uploading…" : "Drop your resume here, or click to browse"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">PDF or DOCX, up to 10MB</p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
          }}
        />
      </div>
      {error ? <p className="mt-2 text-sm text-danger">{error}</p> : null}
    </div>
  );
}
