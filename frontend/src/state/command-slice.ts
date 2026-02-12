import { createSlice } from "@reduxjs/toolkit";

export type Command = {
  content: string;
  type: "input" | "output";
};

/** Maximum terminal commands retained in memory. */
const MAX_COMMANDS = 2_000;

const initialCommands: Command[] = [];

export const commandSlice = createSlice({
  name: "command",
  initialState: {
    commands: initialCommands,
  },
  reducers: {
    appendInput: (state, action) => {
      state.commands.push({ content: action.payload, type: "input" });
      if (state.commands.length > MAX_COMMANDS) {
        state.commands = state.commands.slice(-MAX_COMMANDS);
      }
    },
    appendOutput: (state, action) => {
      state.commands.push({ content: action.payload, type: "output" });
      if (state.commands.length > MAX_COMMANDS) {
        state.commands = state.commands.slice(-MAX_COMMANDS);
      }
    },
    clearTerminal: (state) => {
      state.commands = [];
    },
  },
});

export const { appendInput, appendOutput, clearTerminal } =
  commandSlice.actions;

export default commandSlice.reducer;
