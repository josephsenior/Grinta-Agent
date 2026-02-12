import { combineReducers, configureStore } from "@reduxjs/toolkit";
import agentReducer from "./state/agent-slice";
import browserReducer from "./state/browser-slice";
import initialQueryReducer from "./state/initial-query-slice";
import commandReducer from "./state/command-slice";
import securityAnalyzerReducer from "./state/security-analyzer-slice";
import statusReducer from "./state/status-slice";
import metricsReducer from "./state/metrics-slice";
import eventMessageReducer from "./state/event-message-slice";
import streamingReducer from "./state/streaming-slice";

export const rootReducer = combineReducers({
  initialQuery: initialQueryReducer,
  browser: browserReducer,
  cmd: commandReducer,
  agent: agentReducer,
  securityAnalyzer: securityAnalyzerReducer,
  status: statusReducer,
  metrics: metricsReducer,
  eventMessage: eventMessageReducer,
  streaming: streamingReducer,
});

const store = configureStore({
  reducer: rootReducer,
});

export type RootState = ReturnType<typeof store.getState>;
export type AppStore = typeof store;
export type AppDispatch = typeof store.dispatch;

export default store;
