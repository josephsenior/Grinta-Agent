import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface Notification {
  id: string;
  type: "info" | "success" | "warning" | "error";
  title: string;
  message: string;
  timestamp: number;
  read: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface NotificationsState {
  notifications: Notification[];
}

const initialState: NotificationsState = {
  notifications: [],
};

const notificationsSlice = createSlice({
  name: "notifications",
  initialState,
  reducers: {
    addNotification: (
      state,
      action: PayloadAction<Omit<Notification, "id" | "timestamp" | "read">>,
    ) => {
      const notification: Notification = {
        ...action.payload,
        id: `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: Date.now(),
        read: false,
      };
      state.notifications.unshift(notification);
      // Keep only last 50 notifications
      if (state.notifications.length > 50) {
        state.notifications = state.notifications.slice(0, 50);
      }
    },
    markAsRead: (state, action: PayloadAction<string>) => {
      const notification = state.notifications.find(
        (n) => n.id === action.payload,
      );
      if (notification) {
        notification.read = true;
      }
    },
    markAllAsRead: (state) => {
      state.notifications.forEach((n) => {
        n.read = true;
      });
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(
        (n) => n.id !== action.payload,
      );
    },
    clearAll: (state) => {
      state.notifications = [];
    },
  },
});

export const {
  addNotification,
  markAsRead,
  markAllAsRead,
  removeNotification,
  clearAll,
} = notificationsSlice.actions;

export default notificationsSlice.reducer;
