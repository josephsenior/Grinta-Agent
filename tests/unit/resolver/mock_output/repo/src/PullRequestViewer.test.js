"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const jsx_runtime_1 = require("react/jsx-runtime");
const react_1 = require("@testing-library/react");
const PullRequestViewer_1 = __importDefault(require("./PullRequestViewer"));
describe('PullRequestViewer', () => {
    it('renders the component title', () => {
        (0, react_1.render)((0, jsx_runtime_1.jsx)(PullRequestViewer_1.default, {}));
        const titleElement = react_1.screen.getByText(/Pull Request Viewer/i);
        expect(titleElement).toBeInTheDocument();
    });
    it('renders the repository select dropdown', () => {
        (0, react_1.render)((0, jsx_runtime_1.jsx)(PullRequestViewer_1.default, {}));
        const selectElement = react_1.screen.getByRole('combobox', { name: /select a repository/i });
        expect(selectElement).toBeInTheDocument();
    });
});
