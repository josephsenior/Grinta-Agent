import { createSlice } from "@reduxjs/toolkit";

/** Maximum submitted event IDs retained (auto-evict oldest). */
const MAX_SUBMITTED_EVENT_IDS = 500;

export const eventMessageSlice = createSlice({
  name: "eventMessage",
  initialState: {
    submittedEventIds: [] as number[], // Avoid the flashing issue of the confirmation buttons
  },
  reducers: {
    addSubmittedEventId: (state, action) => {
      state.submittedEventIds.push(action.payload);
      if (state.submittedEventIds.length > MAX_SUBMITTED_EVENT_IDS) {
        state.submittedEventIds = state.submittedEventIds.slice(
          -MAX_SUBMITTED_EVENT_IDS,
        );
      }
    },
    removeSubmittedEventId: (state, action) => {
      state.submittedEventIds = state.submittedEventIds.filter(
        (id) => id !== action.payload,
      );
    },
  },
});

export const { addSubmittedEventId, removeSubmittedEventId } =
  eventMessageSlice.actions;

export default eventMessageSlice.reducer;
