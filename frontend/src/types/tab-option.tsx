enum TabOption {
  PLANNER = "planner",
  BROWSER = "browser",
}

type TabType = TabOption.PLANNER | TabOption.BROWSER;

const AllTabs = [TabOption.BROWSER, TabOption.PLANNER];

export { AllTabs, TabOption, type TabType };
