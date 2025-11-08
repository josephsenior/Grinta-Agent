import { PayloadAction } from "@reduxjs/toolkit";
import { ForgeObservation } from "./types/core/observations";
import { ForgeAction } from "./types/core/actions";

export type Message = {
  sender: "user" | "assistant";
  content: string;
  timestamp: string;
  imageUrls?: string[];
  type?: "thought" | "error" | "action";
  success?: boolean;
  pending?: boolean;
  translationID?: string;
  eventID?: number;
  observation?: PayloadAction<ForgeObservation>;
  action?: PayloadAction<ForgeAction>;
};
