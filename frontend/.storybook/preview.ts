import type { Preview } from "@storybook/react-vite";
import { MINIMAL_VIEWPORTS } from "storybook/viewport";
import "../src/index.css";
import "../src/App.css";

const preview: Preview = {
  parameters: {
    controls: { matchers: { color: /(background|color)$/i } },
    viewport: {
      options: MINIMAL_VIEWPORTS,
    },
  },
};

export default preview;
