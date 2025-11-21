import React, { useState, useEffect } from 'react';
import { Octokit } from '@octokit/rest';
import Select from 'react-select';

const importMetaToken =
  (globalThis as { importMeta?: { env?: Record<string, string | undefined> } }).importMeta?.env
    ?.VITE_GITHUB_TOKEN;
const authToken =
  (typeof process !== 'undefined' && process.env?.VITE_GITHUB_TOKEN) ||
  importMetaToken ||
  '';
const octokit = new Octokit({ auth: authToken });

interface PullRequest {
  title: string;
  html_url: string;
  user: {
    login: string;
  };
}

interface Repo {
  value: string;
  label: string;
}

const PullRequestViewer: React.FC = () => {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repo | null>(null);
  const [pullRequests, setPullRequests] = useState<PullRequest[]>([]);
  const handleRepoChange = (option: Repo | null) => setSelectedRepo(option);

  useEffect(() => {
    const fetchRepos = async () => {
      try {
        const response = await octokit.repos.listForOrg({
          org: 'OpenDevin',
          type: 'all',
        });
        const repoOptions = (response.data as Array<{ name: string }>).map((repo) => ({
          value: repo.name,
          label: repo.name,
        }));
        setRepos(repoOptions);
      } catch (error) {
        console.error('Error fetching repos:', error);
      }
    };
    fetchRepos();
  }, []);

  useEffect(() => {
    const fetchPullRequests = async () => {
      if (selectedRepo) {
        try {
          let allPullRequests: PullRequest[] = [];
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

            const data = response.data as PullRequest[];
            allPullRequests = [...allPullRequests, ...data];

            if (response.data.length < 100) {
              hasNextPage = false;
            } else {
              page++;
            }
          }

          setPullRequests(allPullRequests);
        } catch (error) {
          console.error('Error fetching pull requests:', error);
        }
      }
    };
    fetchPullRequests();
  }, [selectedRepo]);

  return (
    <div>
      <h1>Pull Request Viewer</h1>
      <Select
        options={repos}
        value={selectedRepo}
        onChange={handleRepoChange}
        placeholder="Select a repository"
        aria-label="Select a repository"
      />
      {pullRequests.length > 0 ? (
        <ul>
          {pullRequests.map((pr) => (
            <li key={pr.html_url}>
              <a href={pr.html_url} target="_blank" rel="noopener noreferrer">
                {pr.title}
              </a>
              {' by '}
              {pr.user.login}
            </li>
          ))}
        </ul>
      ) : (
        <p>No open pull requests found.</p>
      )}
    </div>
  );
};

export default PullRequestViewer;
