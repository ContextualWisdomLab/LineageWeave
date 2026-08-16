import type { Preview } from "@storybook/react-vite";
import "../src/index.css";
import "../src/App.css";

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    docs: {
      description: {
        component:
          "Click a person or organization chip to continue the walk. When the caption says multiple organizations, open the Keyman list.",
      },
    },
  },
};

export default preview;
