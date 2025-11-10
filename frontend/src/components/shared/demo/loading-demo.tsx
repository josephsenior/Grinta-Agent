import React, { useState } from "react";
import { LoadingSpinner } from "../loading-spinner";
import {
  SkeletonCard,
  SkeletonDropdown,
  SkeletonForm,
  SkeletonTable,
} from "../loading/skeleton-loader";
import {
  LoadingButton,
  LoadingCard,
  LoadingTable,
  LoadingOverlay,
} from "../loading/loading-state";
import { ErrorBoundary } from "../error/error-boundary";
import { ErrorMessageBanner } from "../../features/chat/error-message-banner";
import { useToastHelpers } from "../notifications/toast";
import {
  useLoadingState,
  useAsyncOperation,
} from "../../../hooks/use-loading-state";
import { CustomDropdown } from "../inputs/custom-dropdown";

// Demo component that throws an error
function ErrorThrowingComponent() {
  const [shouldThrow, setShouldThrow] = useState(false);

  if (shouldThrow) {
    throw new Error("This is a demo error for testing error boundaries!");
  }

  return (
    <div className="p-4 bg-background-elevated rounded-xl border border-border-glass">
      <h3 className="text-lg font-semibold mb-2">Error Boundary Demo</h3>
      <p className="text-sm text-text-secondary mb-4">
        Click the button below to trigger an error that will be caught by the
        ErrorBoundary.
      </p>
      <button
        type="button"
        onClick={() => setShouldThrow(true)}
        className="px-4 py-2 bg-danger-DEFAULT text-white rounded-lg hover:bg-danger-DEFAULT/80 transition-colors"
      >
        Throw Error
      </button>
    </div>
  );
}

export function LoadingDemo() {
  const [showSkeletons, setShowSkeletons] = useState(false);
  const [showLoadingStates, setShowLoadingStates] = useState(false);
  const [showErrorBanner, setShowErrorBanner] = useState(false);
  const { success, error, warning, info } = useToastHelpers();
  const { isLoading, withLoading } = useLoadingState({
    delay: 500,
    minDuration: 1000,
  });
  const {
    isLoading: asyncLoading,
    error: asyncError,
    execute,
  } = useAsyncOperation();

  const simulateAsyncOperation = async () => {
    await new Promise((resolve) => {
      setTimeout(resolve, 2000);
    });
    if (Math.random() > 0.5) {
      throw new Error("Simulated API error");
    }
    return "Operation completed successfully!";
  };

  const handleAsyncOperation = () => {
    execute(simulateAsyncOperation)
      .then((result) => success("Success!", result))
      .catch((err) => error("Error!", err.message));
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-text-primary mb-2">
          Loading States & Error Handling Demo
        </h1>
        <p className="text-text-secondary">
          Comprehensive showcase of all loading and error components
        </p>
      </div>

      {/* Loading Spinners */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold text-text-primary">
          Loading Spinners
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-background-elevated rounded-xl border border-border-glass text-center">
            <h3 className="text-sm font-medium mb-2">Default</h3>
            <LoadingSpinner size="medium" />
          </div>
          <div className="p-4 bg-background-elevated rounded-xl border border-border-glass text-center">
            <h3 className="text-sm font-medium mb-2">Dots</h3>
            <LoadingSpinner size="medium" variant="dots" />
          </div>
          <div className="p-4 bg-background-elevated rounded-xl border border-border-glass text-center">
            <h3 className="text-sm font-medium mb-2">Pulse</h3>
            <LoadingSpinner size="medium" variant="pulse" />
          </div>
          <div className="p-4 bg-background-elevated rounded-xl border border-border-glass text-center">
            <h3 className="text-sm font-medium mb-2">Bars</h3>
            <LoadingSpinner size="medium" variant="bars" />
          </div>
        </div>
      </section>

      {/* Skeleton Loaders */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-text-primary">
            Skeleton Loaders
          </h2>
          <button
            type="button"
            onClick={() => setShowSkeletons(!showSkeletons)}
            className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            {showSkeletons ? "Hide" : "Show"} Skeletons
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Card Skeleton</h3>
            <SkeletonCard />
          </div>
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Form Skeleton</h3>
            <SkeletonForm />
          </div>
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Dropdown Skeleton</h3>
            <SkeletonDropdown />
          </div>
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Table Skeleton</h3>
            <SkeletonTable rows={3} />
          </div>
        </div>
      </section>

      {/* Loading States */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-text-primary">
            Loading States
          </h2>
          <button
            type="button"
            onClick={() => setShowLoadingStates(!showLoadingStates)}
            className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            {showLoadingStates ? "Hide" : "Show"} Loading States
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Loading Button</h3>
            <LoadingButton
              isLoading={isLoading}
              type="button"
              onClick={() =>
                withLoading(async () => {
                  await new Promise((resolve) => {
                    setTimeout(resolve, 2000);
                  });
                })
              }
            >
              Click me!
            </LoadingButton>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-medium">Loading Card</h3>
            <LoadingCard isLoading={showLoadingStates}>
              <div className="p-4">
                <h4 className="font-semibold">Card Content</h4>
                <p className="text-sm text-text-secondary">
                  This content is hidden when loading
                </p>
              </div>
            </LoadingCard>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-medium">Loading Table</h3>
            <LoadingTable isLoading={showLoadingStates}>
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="text-left p-2">Name</th>
                    <th className="text-left p-2">Status</th>
                    <th className="text-left p-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="p-2">John Doe</td>
                    <td className="p-2">Active</td>
                    <td className="p-2">Edit</td>
                  </tr>
                </tbody>
              </table>
            </LoadingTable>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-medium">Loading Overlay</h3>
            <LoadingOverlay
              isLoading={showLoadingStates}
              loadingText="Processing..."
            >
              <div className="p-8 bg-background-elevated rounded-xl border border-border-glass text-center">
                <h4 className="font-semibold mb-2">Overlay Demo</h4>
                <p className="text-sm text-text-secondary">
                  This content is overlaid when loading
                </p>
              </div>
            </LoadingOverlay>
          </div>
        </div>
      </section>

      {/* Error Handling */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold text-text-primary">
          Error Handling
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Error Banner</h3>
            <button
              type="button"
              onClick={() => setShowErrorBanner(!showErrorBanner)}
              className="px-4 py-2 bg-danger-DEFAULT text-white rounded-lg hover:bg-danger-DEFAULT/80 transition-colors"
            >
              {showErrorBanner ? "Hide" : "Show"} Error Banner
            </button>
            {showErrorBanner && (
              <ErrorMessageBanner
                message="This is a demo error message"
                type="error"
                onRetry={() => setShowErrorBanner(false)}
                showDetails
              />
            )}
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-medium">Error Boundary</h3>
            <ErrorBoundary>
              <ErrorThrowingComponent />
            </ErrorBoundary>
          </div>
        </div>
      </section>

      {/* Toast Notifications */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold text-text-primary">
          Toast Notifications
        </h2>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() =>
              success("Success!", "Operation completed successfully")
            }
            className="px-4 py-2 bg-success-DEFAULT text-white rounded-lg hover:bg-success-DEFAULT/80 transition-colors"
          >
            Success Toast
          </button>
          <button
            type="button"
            onClick={() => error("Error!", "Something went wrong")}
            className="px-4 py-2 bg-danger-DEFAULT text-white rounded-lg hover:bg-danger-DEFAULT/80 transition-colors"
          >
            Error Toast
          </button>
          <button
            type="button"
            onClick={() => warning("Warning!", "Please check your input")}
            className="px-4 py-2 bg-warning-DEFAULT text-white rounded-lg hover:bg-warning-DEFAULT/80 transition-colors"
          >
            Warning Toast
          </button>
          <button
            type="button"
            onClick={() => info("Info", "Here's some helpful information")}
            className="px-4 py-2 bg-info-DEFAULT text-white rounded-lg hover:bg-info-DEFAULT/80 transition-colors"
          >
            Info Toast
          </button>
        </div>
      </section>

      {/* Async Operations */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold text-text-primary">
          Async Operations
        </h2>
        <div className="space-y-4">
          <button
            type="button"
            onClick={handleAsyncOperation}
            disabled={asyncLoading}
            className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 transition-colors"
          >
            {asyncLoading ? "Processing..." : "Simulate Async Operation"}
          </button>
          {asyncError && (
            <div className="p-4 bg-danger-DEFAULT/10 border border-danger-DEFAULT/20 rounded-lg text-danger-DEFAULT">
              <strong>Error:</strong> {asyncError.message}
            </div>
          )}
        </div>
      </section>

      {/* Enhanced Dropdowns */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold text-text-primary">
          Enhanced Dropdowns
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-sm font-medium">Loading Dropdown</label>
            <CustomDropdown
              items={[
                { key: "option1", label: "Option 1" },
                { key: "option2", label: "Option 2" },
                { key: "option3", label: "Option 3" },
              ]}
              placeholder="Select an option"
              isLoading={showLoadingStates}
              loadingText="Loading options..."
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Error Dropdown</label>
            <CustomDropdown
              items={[
                { key: "option1", label: "Option 1" },
                { key: "option2", label: "Option 2" },
                { key: "option3", label: "Option 3" },
              ]}
              placeholder="Select an option"
              error={showErrorBanner ? "This field is required" : undefined}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
