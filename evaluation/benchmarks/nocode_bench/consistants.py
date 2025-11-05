DOCPATH_PATTERNS = ["docs/", "^CHANGES\\.rst$", "doc/", "ChangeLog", "^changelog/", "^CHANGES$"]
MATPLOTLIB_CONFIG = (
    {
        k: {
            "python": "3.11",
            "conda_env": "matplotlib_35",
            "install": "python -m pip install -e .",
            "test_cmd": "pytest -rA --color=no",
        }
        for k in ["3.5", "3.6", "3.7", "3.8", "3.9"]
    }
    | {
        k: {
            "python": "3.8",
            "conda_env": "matplotlib_31",
            "install": "python -m pip install -e .",
            "test_cmd": "pytest -rA --color=no",
        }
        for k in ["3.1", "3.2", "3.3", "3.4"]
    }
    | {
        k: {
            "python": "3.5",
            "install": "python setup.py build; python setup.py install",
            "conda_env": "matplotlib_11",
            "nonroot": True,
            "test_cmd": "pytest -rA --color=no",
        }
        for k in ["2.0", "2.1", "2.2", "1.0", "1.1", "1.2", "1.3", "1.4", "1.5"]
    }
)
for k in ["3.8", "3.9"]:
    MATPLOTLIB_CONFIG[k]["install"] = 'python -m pip install --no-build-isolation -e ".[dev]"'
SYMPY_CONFIG = {"1.0": {"conda_env": "sympy_10", "install": "pip install -e .", "test_cmd": "bin/test -C -v"}}
REQUESTS_CONFIG = {
    k: {
        "conda_env": "requests_227",
        "install": "pip install -r requirements-dev.txt",
        "test_cmd": "pytest -rA",
    }
    for k in ["2.27"]
} | {
    k: {
        "conda_env": "requests_226",
        "install": "pip install -e .",
        "test_cmd": "pytest -rA",
    }
    for k in ["2.26"]
}
PYTEST_CONFIG = dict(
    {
        k: {"conda_env": "pytest_33", "install": "pip install -e .", "test_cmd": "pytest -v --color=no"}
        for k in ["4.4", "4.1", "3.7", "3.4", "3.3"]
    }
)
PYLINT_CONFIG = {
    k: {
        "conda_env": "pylint_210",
        "install": "pip install -r requirements_test.txt",
        "test_cmd": "pytest -rA --color=no",
    }
    for k in [
        "2.10",
        "2.11",
        "2.13",
        "2.14",
        "2.15",
        "2.16",
        "2.17",
        "3.0",
        "3.1",
        "3.2",
        "3.3",
    ]
} | {
    k: {
        "conda_env": "pylint_210",
        "pre_install": ["sed -i 's/setuptools==[0-9.]\\+/setuptools==58.0.0/' requirements_test_min.txt"],
        "install": "pip install -r requirements_test.txt",
        "test_cmd": "pytest -rA --color=no",
    }
    for k in ["3.0", "3.1", "3.2", "3.3"]
}
ASTROPY_CONFIG = (
    {
        k: {
            "conda_env": "astropy_11",
            "install": "python -m pip install -e .[test] --verbose",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["1.1", "1.2", "1.3", "2.0"]
    }
    | {
        k: {
            "conda_env": "astropy_30",
            "pre_install": "echo '[pytest]\nfilterwarnings =\n    ignore::DeprecationWarning' > pytest.ini",
            "install": "python -m pip install -e .[test] --verbose",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["3.0", "3.1", "3.2"]
    }
    | {
        k: {
            "conda_env": "astropy_40",
            "pre_install": [
                'sed -i \'s/requires = \\["setuptools",/requires = \\["setuptools==68.0.0",/\' pyproject.toml'
            ],
            "install": "python -m pip install -e .[test] --verbose",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["4.0"]
    }
    | {
        k: {
            "conda_env": "astropy_41",
            "pre_install": [
                'sed -i \'s/requires = \\["setuptools",/requires = \\["setuptools==68.0.0",/\' pyproject.toml',
                "sed -i 's/^qt_no_exception_capture = 1$/; qt_no_exception_capture = 1/' setup.cfg",
                'sed -i \'/setuptools==68.0.0",/a \\    "markupsafe==2.0.1",\' pyproject.tomlsed -i \'/setuptools==68.0.0",/a \\    "markupsafe==2.0.1",\' pyproject.toml',
            ],
            "install": "python -m pip install -e .[test] --verbose",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["4.1"]
    }
    | {
        k: {
            "conda_env": "astropy_42",
            "pre_install": [
                'sed -i \'s/requires = \\["setuptools",/requires = \\["setuptools==68.0.0",/\' pyproject.toml',
                'sed -i \'/setuptools==68.0.0",/a \\    "markupsafe==2.0.1",\' pyproject.tomlsed -i \'/setuptools==68.0.0",/a \\    "markupsafe==2.0.1",\' pyproject.toml',
            ],
            "install": "python -m pip install -e .[test] --verbose",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["4.2", "4.3", "5.0", "5.1"]
    }
    | {
        k: {
            "conda_env": "astropy_52",
            "pre_install": [
                'sed -i \'s/requires = \\["setuptools",/requires = \\["setuptools==68.0.0",/\' pyproject.toml'
            ],
            "install": "python -m pip install -e .[test] --verbose",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["5.2", "5.3", "6.0", "6.1", "7.0"]
    }
)
DJANGO_CONFIG = {
    k: {
        "install": "pip install -e .",
        "conda_env": "django_22",
        "test_cmd": "python tests/runtests.py --verbosity 2",
    }
    for k in ["1.9", "2.2"]
} | {
    "3.2": {
        "install": "pip install -e .",
        "conda_env": "django_32",
        "test_cmd": "python tests/runtests.py --verbosity 2",
    },
    "4.2": {
        "install": "pip install -e .",
        "conda_env": "django_42",
        "test_cmd": "python tests/runtests.py --verbosity 2",
    },
    "5.1": {
        "install": "pip install -e .",
        "conda_env": "django_51",
        "test_cmd": "python tests/runtests.py --verbosity 2",
    },
}
SPHINX_CONFIG = (
    {
        k: {
            "conda_env": "sphinx_20",
            "install": "python -m pip install -e .[test]",
            "pre_install": ["sed -i 's/pytest/pytest -rA/' tox.ini"],
            "test_cmd": "tox --current-env -epy37 -v --",
        }
        for k in ["1.3", "1.4", "1.5", "1.6", "1.7", "1.8"]
    }
    | {
        k: {
            "conda_env": "sphinx_20",
            "install": "python -m pip install -e .[test]",
            "pre_install": [
                "sed -i 's/pytest/pytest -rA/' tox.ini",
                "sed -i 's/Jinja2>=2.3/Jinja2<3.0/' setup.py",
            ],
            "test_cmd": "tox --current-env -epy37 -v --",
        }
        for k in ["2.0", "2.1", "2.2", "2.3", "2.4"]
    }
    | {
        k: {
            "conda_env": "sphinx_30",
            "install": "python -m pip install -e .[test]",
            "pre_install": [
                "sed -i 's/pytest/pytest -rA/' tox.ini",
                "sed -i 's/Jinja2>=2.3/Jinja2<3.0/' setup.py",
                "sed -i 's/sphinxcontrib-applehelp/sphinxcontrib-applehelp<=1.0.7/' setup.py",
                "sed -i 's/sphinxcontrib-devhelp/sphinxcontrib-devhelp<=1.0.5/' setup.py",
                "sed -i 's/sphinxcontrib-qthelp/sphinxcontrib-qthelp<=1.0.6/' setup.py",
                "sed -i 's/alabaster>=0.7,<0.8/alabaster>=0.7,<0.7.12/' setup.py",
                "sed -i \"s/'packaging',/'packaging', 'markupsafe<=2.0.1',/\" setup.py",
                "sed -i 's/sphinxcontrib-htmlhelp/sphinxcontrib-htmlhelp<=2.0.4/' setup.py",
                "sed -i 's/sphinxcontrib-serializinghtml/sphinxcontrib-serializinghtml<=1.1.9/' setup.py",
            ],
            "test_cmd": "tox --current-env -epy37 -v --",
        }
        for k in ["3.0", "3.1", "3.2", "3.3", "3.4", "3.5", "4.0"]
    }
    | {
        k: {
            "conda_env": "sphinx_30",
            "install": "python -m pip install -e .[test]",
            "pre_install": [
                "sed -i 's/pytest/pytest -rA/' tox.ini",
                "sed -i 's/Jinja2>=2.3/Jinja2<3.0/' setup.py",
                "sed -i 's/sphinxcontrib-applehelp/sphinxcontrib-applehelp<=1.0.7/' setup.py",
                "sed -i 's/sphinxcontrib-devhelp/sphinxcontrib-devhelp<=1.0.5/' setup.py",
                "sed -i 's/sphinxcontrib-qthelp/sphinxcontrib-qthelp<=1.0.6/' setup.py",
                "sed -i 's/alabaster>=0.7,<0.8/alabaster>=0.7,<0.7.12/' setup.py",
                "sed -i \"s/'packaging',/'packaging', 'markupsafe<=2.0.1',/\" setup.py",
                "grep -q 'sphinxcontrib-htmlhelp>=2.0.0' setup.py && sed -i 's/sphinxcontrib-htmlhelp>=2.0.0/sphinxcontrib-htmlhelp>=2.0.0,<=2.0.4/' setup.py || sed -i 's/sphinxcontrib-htmlhelp/sphinxcontrib-htmlhelp<=2.0.4/' setup.py",
                "grep -q 'sphinxcontrib-serializinghtml>=1.1.5' setup.py && sed -i 's/sphinxcontrib-serializinghtml>=1.1.5/sphinxcontrib-serializinghtml>=1.1.5,<=1.1.9/' setup.py || sed -i 's/sphinxcontrib-serializinghtml/sphinxcontrib-serializinghtml<=1.1.9/' setup.py",
            ],
            "test_cmd": "tox --current-env -epy37 -v --",
        }
        for k in ["4.1"]
    }
    | {
        k: {
            "conda_env": "sphinx_30",
            "install": "python -m pip install -e .[test]",
            "pre_install": [
                "sed -i 's/pytest/pytest -rA/' tox.ini",
                "sed -i 's/Jinja2>=2.3/Jinja2<3.0/' setup.py",
                "sed -i 's/sphinxcontrib-applehelp/sphinxcontrib-applehelp<=1.0.7/' setup.py",
                "sed -i 's/sphinxcontrib-devhelp/sphinxcontrib-devhelp<=1.0.5/' setup.py",
                "sed -i 's/sphinxcontrib-qthelp/sphinxcontrib-qthelp<=1.0.6/' setup.py",
                "sed -i 's/alabaster>=0.7,<0.8/alabaster>=0.7,<0.7.12/' setup.py",
                "sed -i \"s/'packaging',/'packaging', 'markupsafe<=2.0.1',/\" setup.py",
                "sed -i 's/sphinxcontrib-htmlhelp>=2.0.0/sphinxcontrib-htmlhelp>=2.0.0,<=2.0.4/' setup.py",
                "sed -i 's/sphinxcontrib-serializinghtml>=1.1.5/sphinxcontrib-serializinghtml>=1.1.5,<=1.1.9/' setup.py",
            ],
            "test_cmd": "tox --current-env -epy37 -v --",
        }
        for k in ["4.2", "4.3", "4.4"]
    }
    | {
        k: {
            "conda_env": "sphinx_30",
            "install": "python -m pip install -e .[test]",
            "pre_install": ["sed -i 's/pytest/pytest -rA/' tox.ini"],
            "test_cmd": "tox --current-env -epy37 -v --",
        }
        for k in ["4.5", "5.0", "5.1", "5.2"]
    }
    | {
        k: {
            "conda_env": "sphinx_60",
            "install": "python -m pip install -e .[test]",
            "pre_install": ["sed -i 's/pytest/pytest -rA/' tox.ini"],
            "test_cmd": "tox --current-env -epy39 -v --",
        }
        for k in ["6.0", "6.2", "7.0", "7.1"]
    }
    | {
        k: {
            "conda_env": "sphinx_72",
            "install": "python -m pip install -e .[test]",
            "pre_install": [
                "sed -i 's/pytest/pytest -rA/' tox.ini",
                "apt-get update && apt-get install -y graphviz",
            ],
            "test_cmd": "tox --current-env -epy39 -v --",
        }
        for k in ["7.2", "7.3", "7.4"]
    }
    | {
        k: {
            "conda_env": "sphinx_80",
            "install": "python -m pip install -e .[test]",
            "pre_install": ["sed -i 's/pytest/pytest -rA/' tox.ini"],
            "test_cmd": "tox --current-env -epy310 -v --",
        }
        for k in ["8.0", "8.1"]
    }
)
SKLEARN_CONFIG = (
    {
        k: {
            "conda_env": "skl_020",
            "install": "pip install -v --no-use-pep517 --no-build-isolation -e .",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["0.20", "0.21", "0.22"]
    }
    | {
        k: {
            "conda_env": "skl_100",
            "install": "pip install -v --no-use-pep517 --no-build-isolation -e .",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["0.23", "0.24", "1.00", "1.01", "1.02"]
    }
    | {
        k: {
            "conda_env": "skl_104",
            "install": "pip install -v --no-use-pep517 --no-build-isolation -e .",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["1.03", "1.04", "1.05"]
    }
)
SEABORN_CONFIG = dict(
    {
        k: {"conda_env": "seaborn_010", "install": "pip install -e .[dev]", "test_cmd": "pytest --color=no -rA"}
        for k in ["0.3", "0.4", "0.5", "0.6", "0.11", "0.12", "0.13", "0.14"]
    }
)
XARRAY_CONFIG = (
    {
        k: {
            "conda_env": "xarray_0014",
            "install": "pip install -e .",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["0014", "0015", "0016"]
    }
    | {
        k: {
            "conda_env": "xarray_0017",
            "install": "pip install -e .",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["0017", "0018", "0019", "0020", "0021"]
    }
    | {
        k: {
            "conda_env": "xarray_2203",
            "install": "pip install -e .",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["2203", "2206", "2209", "2210", "2211", "2212"]
    }
    | {
        k: {
            "conda_env": "xarray_2303",
            "install": "pip install -e .",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in [
            "2303",
            "2304",
            "2305",
            "2306",
            "2308",
            "2309",
            "2310",
            "2311",
            "2312",
        ]
    }
    | {
        k: {
            "conda_env": "xarray_2401",
            "install": "pip install -e .",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in [
            "2401",
            "2402",
            "2403",
            "2405",
            "2407",
            "2409",
            "2410",
            "2411",
        ]
    }
)
SKLEARN_CONFIG = (
    {
        k: {
            "conda_env": "skl_020",
            "install": "pip install -v --no-use-pep517 --no-build-isolation -e .",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["0.20", "0.21", "0.22"]
    }
    | {
        k: {
            "conda_env": "skl_100",
            "install": "pip install -v --no-use-pep517 --no-build-isolation -e .",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["0.23", "0.24", "1.00", "1.01", "1.02"]
    }
    | {
        k: {
            "conda_env": "skl_104",
            "install": "pip install -v --no-use-pep517 --no-build-isolation -e .",
            "test_cmd": "pytest --color=no -rA",
        }
        for k in ["1.03", "1.04", "1.05", "1.06", "1.07"]
    }
)
MAP_REPO_TO_CONFIG = {
    "pydata/xarray": XARRAY_CONFIG,
    "mwaskom/seaborn": SEABORN_CONFIG,
    "scikit-learn/scikit-learn": SKLEARN_CONFIG,
    "sphinx-doc/sphinx": SPHINX_CONFIG,
    "django/django": DJANGO_CONFIG,
    "astropy/astropy": ASTROPY_CONFIG,
    "pylint-dev/pylint": PYLINT_CONFIG,
    "pytest-dev/pytest": PYTEST_CONFIG,
    "psf/requests": REQUESTS_CONFIG,
    "sympy/sympy": SYMPY_CONFIG,
    "matplotlib/matplotlib": MATPLOTLIB_CONFIG,
}
