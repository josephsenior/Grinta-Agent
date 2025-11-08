import Clip from "#/icons/clip.svg?react";

interface UploadImageInputProps {
  onUpload: (files: File[]) => void;
  label?: React.ReactNode;
  inputTestId?: string;
}

export function UploadImageInput({ onUpload, label, inputTestId }: UploadImageInputProps) {
  const handleUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      onUpload(Array.from(event.target.files));
    }
  };

  return (
    <label className="cursor-pointer py-[10px]">
      {label || <Clip data-testid="default-label" width={24} height={24} />}
      <input
        data-testid={inputTestId ?? "upload-image-input"}
        type="file"
        multiple
        hidden
        onChange={handleUpload}
      />
    </label>
  );
}
