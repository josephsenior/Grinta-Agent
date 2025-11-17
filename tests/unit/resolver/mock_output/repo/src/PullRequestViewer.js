"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const jsx_runtime_1 = require("react/jsx-runtime");
const react_1 = require("react");
const rest_1 = require("@octokit/rest");
const react_select_1 = __importDefault(require("react-select"));
const importMetaToken = globalThis.importMeta?.env
    ?.VITE_GITHUB_TOKEN;
const authToken = (typeof process !== 'undefined' && process.env?.VITE_GITHUB_TOKEN) ||
    importMetaToken ||
    '';
const octokit = new rest_1.Octokit({ auth: authToken });
const PullRequestViewer = () => {
    const [repos, setRepos] = (0, react_1.useState)([]);
    const [selectedRepo, setSelectedRepo] = (0, react_1.useState)(null);
    const [pullRequests, setPullRequests] = (0, react_1.useState)([]);
    const handleRepoChange = (option) => setSelectedRepo(option);
    (0, react_1.useEffect)(() => {
        const fetchRepos = async () => {
            try {
                const response = await octokit.repos.listForOrg({
                    org: 'OpenDevin',
                    type: 'all',
                });
                const repoOptions = response.data.map((repo) => ({
                    value: repo.name,
                    label: repo.name,
                }));
                setRepos(repoOptions);
            }
            catch (error) {
                console.error('Error fetching repos:', error);
            }
        };
        fetchRepos();
    }, []);
    (0, react_1.useEffect)(() => {
        const fetchPullRequests = async () => {
            if (selectedRepo) {
                try {
                    let allPullRequests = [];
                    let page = 1;
                    let hasNextPage = true;
                    while (hasNextPage) {
                        const response = await octokit.pulls.list({
                            owner: 'OpenDevin',
                            repo: selectedRepo.value,
                            state: 'open',
                            per_page: 100,
                            page: page,
                        });
                        const data = response.data;
                        allPullRequests = [...allPullRequests, ...data];
                        if (response.data.length < 100) {
                            hasNextPage = false;
                        }
                        else {
                            page++;
                        }
                    }
                    setPullRequests(allPullRequests);
                }
                catch (error) {
                    console.error('Error fetching pull requests:', error);
                }
            }
        };
        fetchPullRequests();
    }, [selectedRepo]);
    return ((0, jsx_runtime_1.jsxs)("div", { children: [(0, jsx_runtime_1.jsx)("h1", { children: "Pull Request Viewer" }), (0, jsx_runtime_1.jsx)(react_select_1.default, { options: repos, value: selectedRepo, onChange: handleRepoChange, placeholder: "Select a repository", "aria-label": "Select a repository" }), pullRequests.length > 0 ? ((0, jsx_runtime_1.jsx)("ul", { children: pullRequests.map((pr) => ((0, jsx_runtime_1.jsxs)("li", { children: [(0, jsx_runtime_1.jsx)("a", { href: pr.html_url, target: "_blank", rel: "noopener noreferrer", children: pr.title }), ' by ', pr.user.login] }, pr.html_url))) })) : ((0, jsx_runtime_1.jsx)("p", { children: "No open pull requests found." }))] }));
};
exports.default = PullRequestViewer;
