import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "../../test-utils";
import { InteractiveChatBox } from "#/components/features/chat/interactive-chat-box";

describe("InteractiveChatBox", () => {
  const onSubmitMock = vi.fn();
  const onStopMock = vi.fn();

  beforeAll(() => {
    global.URL.createObjectURL = vi
      .fn()
      .mockReturnValue("blob:http://example.com");
    global.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

const getUser = () => userEvent.setup();

const confirmFileUpload = async (
  user: ReturnType<typeof userEvent.setup>,
  options: { optional?: boolean } = {},
) => {
  const { optional = false } = options;
  await new Promise((resolve) => setTimeout(resolve, 0));
  const confirmButton = screen.queryByRole("button", { name: /upload/i });
  if (!confirmButton) {
    if (optional) {
      return;
    }
    throw new Error("Expected upload confirmation modal to be visible");
  }
  await user.click(confirmButton);
};

  it("should render", () => {
    renderWithProviders(<InteractiveChatBox onSubmit={onSubmitMock} onStop={onStopMock} />);

    const chatBox = screen.getByTestId("interactive-chat-box");
    within(chatBox).getByTestId("chat-input");
    within(chatBox).getByTestId("upload-image-input");
  });

  it.fails("should set custom values", () => {
    renderWithProviders(
      <InteractiveChatBox
        onSubmit={onSubmitMock}
        onStop={onStopMock}
        value="Hello, world!"
      />,
    );

    const chatBox = screen.getByTestId("interactive-chat-box");
    const chatInput = within(chatBox).getByTestId("chat-input");

    expect(chatInput).toHaveValue("Hello, world!");
  });

  it("should display the image previews when images are uploaded", async () => {
    const user = getUser();
    renderWithProviders(<InteractiveChatBox onSubmit={onSubmitMock} onStop={onStopMock} />);

    const file = new File(["(⌐□_□)"], "chucknorris.png", { type: "image/png" });
    const input = screen.getByTestId("upload-image-input");

    expect(screen.queryAllByTestId("image-preview")).toHaveLength(0);

    await user.upload(input, file);
    await confirmFileUpload(user, { optional: true });
    expect(screen.queryAllByTestId("image-preview")).toHaveLength(1);

    const files = [
      new File(["(⌐□_□)"], "chucknorris2.png", { type: "image/png" }),
      new File(["(⌐□_□)"], "chucknorris3.png", { type: "image/png" }),
    ];

    await user.upload(input, files);
    await confirmFileUpload(user);
    expect(screen.queryAllByTestId("image-preview")).toHaveLength(3);
  });

  it("should remove the image preview when the close button is clicked", async () => {
    const user = getUser();
    renderWithProviders(<InteractiveChatBox onSubmit={onSubmitMock} onStop={onStopMock} />);

    const file = new File(["(⌐□_□)"], "chucknorris.png", { type: "image/png" });
    const input = screen.getByTestId("upload-image-input");

    await user.upload(input, file);
    await confirmFileUpload(user);
    expect(screen.queryAllByTestId("image-preview")).toHaveLength(1);

    const imagePreview = screen.getByTestId("image-preview");
    const closeButton = within(imagePreview).getByRole("button");
    await user.click(closeButton);

    expect(screen.queryAllByTestId("image-preview")).toHaveLength(0);
  });

  it("should call onSubmit with the message and images", async () => {
    const user = getUser();
    renderWithProviders(<InteractiveChatBox onSubmit={onSubmitMock} onStop={onStopMock} />);

    const textarea = within(screen.getByTestId("chat-input")).getByRole(
      "textbox",
    );
    const input = screen.getByTestId("upload-image-input");
    const file = new File(["(⌐□_□)"], "chucknorris.png", { type: "image/png" });

    await user.upload(input, file);
    await confirmFileUpload(user);
    await user.type(textarea, "Hello, world!");
    await user.keyboard("{Enter}");

    expect(onSubmitMock).toHaveBeenCalledWith("Hello, world!", [file], []);

    // clear images after submission
    expect(screen.queryAllByTestId("image-preview")).toHaveLength(0);
  });

  it("should disable the submit button", async () => {
    const user = getUser();
    renderWithProviders(
      <InteractiveChatBox
        isDisabled
        onSubmit={onSubmitMock}
        onStop={onStopMock}
      />,
    );

    const button = screen.getByRole("button", { name: "BUTTON$SEND" });
    expect(button).toBeDisabled();

    await user.click(button);
    expect(onSubmitMock).not.toHaveBeenCalled();
  });

  it("should display the stop button if set and call onStop when clicked", async () => {
    const user = getUser();
    renderWithProviders(
      <InteractiveChatBox
        mode="stop"
        onSubmit={onSubmitMock}
        onStop={onStopMock}
      />,
    );

    const stopButton = screen.getByTestId("stop-button");
    expect(stopButton).toBeInTheDocument();

    await user.click(stopButton);
    expect(onStopMock).toHaveBeenCalledOnce();
  });

  it("should handle image upload and message submission correctly", async () => {
    const user = getUser();
    const onSubmit = vi.fn();
    const onStop = vi.fn();
    const onChange = vi.fn();

    const { rerender } = renderWithProviders(
      <InteractiveChatBox
        onSubmit={onSubmit}
        onStop={onStop}
        onChange={onChange}
        value="test message"
      />,
    );

    // Upload an image via the upload button - this should NOT clear the text input
    const file = new File(["dummy content"], "test.png", { type: "image/png" });
    const input = screen.getByTestId("upload-image-input");
    await user.upload(input, file);
    await confirmFileUpload(user);

    // Verify text input was not cleared
    expect(screen.getByRole("textbox")).toHaveValue("test message");
    expect(onChange).not.toHaveBeenCalledWith("");

    // Submit the message with image
    const submitButton = screen.getByRole("button", { name: "BUTTON$SEND" });
    await user.click(submitButton);

    // Verify onSubmit was called with the message and image
    expect(onSubmit).toHaveBeenCalledWith("test message", [file], []);

    // Verify onChange was called to clear the text input
    expect(onChange).toHaveBeenCalledWith("");

    // Simulate parent component updating the value prop after the change callback
    rerender(
      <InteractiveChatBox
        onSubmit={onSubmit}
        onStop={onStop}
        onChange={onChange}
        value=""
      />,
    );

    // Verify the text input was cleared in the controlled scenario
    expect(screen.getByRole("textbox")).toHaveValue("");

    // Upload another image - this should NOT clear the text input
    onChange.mockClear();
    const updatedInput = screen.getByTestId("upload-image-input");
    await user.upload(updatedInput, file);
    await confirmFileUpload(user, { optional: true });

    // Verify text input is still empty and onChange was not called
    expect(screen.getByRole("textbox")).toHaveValue("");
    expect(onChange).not.toHaveBeenCalled();
  });
});
