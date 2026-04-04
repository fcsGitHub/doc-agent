"use client";

import { useState, useRef, ChangeEvent, DragEvent } from "react";
import { useIngestDocument } from "@/lib/hooks/use-knowledge";

export function UploadZone() {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { mutate, isPending } = useIngestDocument();

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const processFile = (file?: File) => {
    if (!file) return;

    const validExtensions = [".pdf", ".docx", ".md", ".txt"];
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();

    if (!validExtensions.includes(ext)) {
      alert(`不支持的文件类型: ${ext}。请上传 .pdf, .docx, .md 或 .txt 文件。`);
      return;
    }

    mutate(file, {
      onSuccess: () => {
        // Optional: you could show a success toast here
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      },
      onError: (err) => {
        alert(err.message);
      },
    });
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      processFile(files[0]);
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      processFile(files[0]);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div
      onClick={isPending ? undefined : handleClick}
      onDragOver={isPending ? undefined : handleDragOver}
      onDragLeave={isPending ? undefined : handleDragLeave}
      onDrop={isPending ? undefined : handleDrop}
      className={`relative flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 transition-colors ${
        isDragging
          ? "border-blue-500 bg-blue-50"
          : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
      } ${isPending ? "pointer-events-none opacity-60" : ""}`}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf,.docx,.md,.txt"
        className="hidden"
      />
      
      {isPending ? (
        <div className="flex flex-col items-center">
          <div className="mb-2 h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
          <span className="text-sm font-medium text-gray-600">正在上传并处理文档...</span>
        </div>
      ) : (
        <div className="flex flex-col items-center text-center">
          <svg
            className="mb-3 h-10 w-10 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            ></path>
          </svg>
          <span className="mb-1 font-medium text-gray-700">
            点击或将文件拖拽至此处上传
          </span>
          <span className="text-xs text-gray-500">
            支持的格式: .pdf, .docx, .md, .txt
          </span>
        </div>
      )}
    </div>
  );
}
