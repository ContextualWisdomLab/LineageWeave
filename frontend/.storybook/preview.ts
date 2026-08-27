import type { Preview } from "@storybook/react-vite";
import { MINIMAL_VIEWPORTS } from "storybook/viewport";
import { setLocale } from "../src/i18n";
import "../src/index.css";
import "../src/App.css";

const preview: Preview = {
  decorators: [
    (Story) => {
      setLocale("en");
      return Story();
    },
  ],
  parameters: {
    controls: { matchers: { color: /(background|color)$/i } },
    viewport: {
      options: MINIMAL_VIEWPORTS,
    },
  },
};

export default preview;
