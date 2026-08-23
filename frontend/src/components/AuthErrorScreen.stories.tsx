import type { Meta, StoryObj } from "@storybook/react-vite";
import { AuthErrorScreen } from "./AuthErrorScreen";

const meta = {
  title: "Auth/AuthErrorScreen",
  component: AuthErrorScreen,
  args: {
    brandName: "LineageWeave",
    onRetry: () => {},
  },
} satisfies Meta<typeof AuthErrorScreen>;

export default meta;

type Story = StoryObj<typeof meta>;

export const SessionExpired: Story = {
  args: {
    message: "Token is not active",
  },
};

export const GenericAuthError: Story = {
  args: {
    message: "Unexpected error: invalid_client",
  },
};
