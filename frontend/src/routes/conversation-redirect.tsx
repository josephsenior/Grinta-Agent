import React from "react";
import { useNavigate } from "react-router-dom";

/**
 * Redirect component that redirects from /conversation to /conversations
 */
export default function ConversationRedirect() {
  const navigate = useNavigate();

  React.useEffect(() => {
    navigate("/conversations", { replace: true });
  }, [navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-black">
      <div className="text-white">Redirecting to conversations...</div>
    </div>
  );
}
