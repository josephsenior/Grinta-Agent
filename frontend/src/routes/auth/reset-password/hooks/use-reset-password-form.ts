import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useResetPassword } from "#/hooks/auth/use-password-reset";

interface ValidationErrors {
  email: string | null;
  resetToken: string | null;
  password: string | null;
  confirmPassword: string | null;
}

export function useResetPasswordForm() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const resetPasswordMutation = useResetPassword();

  const [email, setEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errors, setErrors] = useState<ValidationErrors>({
    email: null,
    resetToken: null,
    password: null,
    confirmPassword: null,
  });

  useEffect(() => {
    const token = searchParams.get("token");
    const emailParam = searchParams.get("email");
    if (token) setResetToken(token);
    if (emailParam) setEmail(emailParam);
  }, [searchParams]);

  const validateEmail = (value: string): string | null => {
    if (!value) return "Email is required";
    if (!value.includes("@")) return 'Please include "@" in the email address';
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) return "Please enter a valid email address";
    return null;
  };

  const validateResetToken = (value: string): string | null => {
    if (!value) return "Reset token is required";
    return null;
  };

  const validatePassword = (value: string): string | null => {
    if (!value) return "Password is required";
    if (value.length < 8) return "Password must be at least 8 characters long";
    return null;
  };

  const validateConfirmPassword = (
    value: string,
    passwordValue: string,
  ): string | null => {
    if (!value) return "Please confirm your password";
    if (value !== passwordValue) return "Passwords do not match";
    return null;
  };

  const handleEmailChange = (value: string) => {
    setEmail(value);
    if (errors.email) {
      setErrors((prev) => ({ ...prev, email: validateEmail(value) }));
    }
  };

  const handleResetTokenChange = (value: string) => {
    setResetToken(value);
    if (errors.resetToken) {
      setErrors((prev) => ({ ...prev, resetToken: validateResetToken(value) }));
    }
  };

  const handlePasswordChange = (value: string) => {
    setPassword(value);
    if (errors.password) {
      setErrors((prev) => ({ ...prev, password: validatePassword(value) }));
    }
    if (errors.confirmPassword && confirmPassword) {
      setErrors((prev) => ({
        ...prev,
        confirmPassword: validateConfirmPassword(confirmPassword, value),
      }));
    }
  };

  const handleConfirmPasswordChange = (value: string) => {
    setConfirmPassword(value);
    if (errors.confirmPassword) {
      setErrors((prev) => ({
        ...prev,
        confirmPassword: validateConfirmPassword(value, password),
      }));
    }
  };

  const handleBlur = (field: keyof ValidationErrors) => {
    let validationError: string | null = null;
    switch (field) {
      case "email":
        validationError = validateEmail(email);
        break;
      case "resetToken":
        validationError = validateResetToken(resetToken);
        break;
      case "password":
        validationError = validatePassword(password);
        break;
      case "confirmPassword":
        validationError = validateConfirmPassword(confirmPassword, password);
        break;
      default:
        validationError = null;
        break;
    }
    setErrors((prev) => ({ ...prev, [field]: validationError }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const emailErr = validateEmail(email);
    const resetTokenErr = validateResetToken(resetToken);
    const passwordErr = validatePassword(password);
    const confirmPasswordErr = validateConfirmPassword(
      confirmPassword,
      password,
    );

    const newErrors = {
      email: emailErr,
      resetToken: resetTokenErr,
      password: passwordErr,
      confirmPassword: confirmPasswordErr,
    };
    setErrors(newErrors);

    if (emailErr || resetTokenErr || passwordErr || confirmPasswordErr) {
      return;
    }

    try {
      await resetPasswordMutation.mutateAsync({
        email,
        reset_token: resetToken,
        new_password: password,
      });
      setIsSuccess(true);
      setTimeout(() => {
        navigate("/auth/login");
      }, 3000);
    } catch (err: unknown) {
      const errorMessage =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || "Failed to reset password. Please try again.";
      setError(errorMessage);
    }
  };

  return {
    email,
    resetToken,
    password,
    confirmPassword,
    error,
    errors,
    isSuccess,
    isSubmitting: resetPasswordMutation.isPending,
    handleEmailChange,
    handleResetTokenChange,
    handlePasswordChange,
    handleConfirmPasswordChange,
    handleBlur,
    handleSubmit,
    hasTokenFromUrl: !!searchParams.get("token"),
    hasEmailFromUrl: !!searchParams.get("email"),
  };
}
