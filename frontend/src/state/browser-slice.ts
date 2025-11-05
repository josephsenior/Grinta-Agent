import { createSlice } from "@reduxjs/toolkit";

export const initialState = {
  // URL of browser window (will be set when agent navigates)
  url: "",
};

export const browserSlice = createSlice({
  name: "browser",
  initialState,
  reducers: {
    setUrl: (state, action) => {
      state.url = action.payload;
    },
  },
});

export const { setUrl } = browserSlice.actions;

export default browserSlice.reducer;
