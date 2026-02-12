import { combineReducers, configureStore } from "@reduxjs/toolkit";
import agentReducer from "./state/agent-slice";
import browserReducer from "./state/browser-slice";
import codeReducer from "./state/code-slice";
import fileStateReducer from "./state/file-state-slice";
import initialQueryReducer from "./state/initial-query-slice";
import commandReducer from "./state/command-slice";
import securityAnalyzerReducer from "./state/security-analyzer-slice";
import statusReducer from "./state/status-slice";
import metricsReducer from "./state/metrics-slice";
import eventMessageReducer from "./state/event-message-slice";
import streamingReducer from "./state/streaming-slice";
import notificationsReducer from "./state/notifications-slice";

export const rootReducer = combineReducers({
  fileState: fileStateReducer,
  initialQuery: initialQueryReducer,
  browser: browserReducer,
  code: codeReducer,
  cmd: commandReducer,
  agent: agentReducer,
  securityAnalyzer: securityAnalyzerReducer,
  status: statusReducer,
  metrics: metricsReducer,
  eventMessage: eventMessageReducer,
  streaming: streamingReducer,
  notifications: notificationsReducer,
});

const store = configureStore({
  reducer: rootReducer,
});

export type RootState = ReturnType<typeof store.getState>;
export type AppStore = typeof store;
export type AppDispatch = typeof store.dispatch;

export default store;
