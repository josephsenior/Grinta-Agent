import { useState } from "react";

export type SecretsView = "list" | "add-secret-form" | "edit-secret-form";

export function useSecretsState() {
  const [view, setView] = useState<SecretsView>("list");
  const [selectedSecret, setSelectedSecret] = useState<string | null>(null);
  const [confirmationModalIsVisible, setConfirmationModalIsVisible] =
    useState(false);

  const handleEdit = (secretName: string) => {
    setView("edit-secret-form");
    setSelectedSecret(secretName);
  };

  const handleDelete = (secretName: string) => {
    setConfirmationModalIsVisible(true);
    setSelectedSecret(secretName);
  };

  const handleCancel = () => {
    setView("list");
    setSelectedSecret(null);
  };

  const handleAddNew = () => {
    setView("add-secret-form");
    setSelectedSecret(null);
  };

  const handleConfirmDelete = () => {
    setConfirmationModalIsVisible(false);
  };

  const handleCancelDelete = () => {
    setConfirmationModalIsVisible(false);
    setSelectedSecret(null);
  };

  return {
    view,
    selectedSecret,
    confirmationModalIsVisible,
    handleEdit,
    handleDelete,
    handleCancel,
    handleAddNew,
    handleConfirmDelete,
    handleCancelDelete,
  };
}
