import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useUpdateUser, useUser } from "#/hooks/query/use-users";
import {
  displaySuccessToast,
  displayErrorToast,
} from "#/utils/custom-toast-handlers";

interface UserFormData {
  username: string;
  email: string;
  role: "admin" | "user" | "service";
  is_active: boolean;
  email_verified: boolean;
}

export function useEditUserForm(userId: string | undefined) {
  const navigate = useNavigate();
  const { data: user, isLoading, error } = useUser(userId || "");
  const updateUserMutation = useUpdateUser();

  const [formData, setFormData] = useState<UserFormData>({
    username: "",
    email: "",
    role: "user",
    is_active: true,
    email_verified: false,
  });

  useEffect(() => {
    if (user) {
      setFormData({
        username: user.username || "",
        email: user.email || "",
        role: user.role,
        is_active: user.is_active,
        email_verified: user.email_verified,
      });
    }
  }, [user]);

  const handleFieldChange = (field: string, value: string | boolean) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId) return;

    try {
      await updateUserMutation.mutateAsync({
        userId,
        data: formData,
      });
      displaySuccessToast("User updated successfully");
      navigate("/admin/users");
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message || "Failed to update user";
      displayErrorToast(errorMessage);
    }
  };

  return {
    formData,
    handleFieldChange,
    handleSubmit,
    isLoading,
    error,
    user,
    isSubmitting: updateUserMutation.isPending,
  };
}
