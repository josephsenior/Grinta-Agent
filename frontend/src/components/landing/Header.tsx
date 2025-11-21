import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ThemeToggle } from "#/components/ui/theme-toggle";

// Register ScrollTrigger
if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

export default function Header() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const headerRef = useRef<HTMLElement>(null);
  const logoRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // GSAP scroll effects for header
  useEffect(() => {
    if (!headerRef.current || typeof window === "undefined") {
      return () => {
        // No cleanup needed
      };
    }

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReducedMotion) {
      return () => {
        // No cleanup needed for reduced motion
      };
    }

    const header = headerRef.current;

    // Smooth header background transition on scroll
    ScrollTrigger.create({
      trigger: document.body,
      start: "top -80",
      end: "top -100",
      onEnter: () => {
        gsap.to(header, {
          backgroundColor: "var(--bg-glass)",
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
          borderBottom: "1px solid var(--border-subtle)",
          duration: 0.3,
          ease: "power2.out",
        });
      },
      onLeaveBack: () => {
        gsap.to(header, {
          backgroundColor: "transparent",
          backdropFilter: "blur(0px)",
          WebkitBackdropFilter: "blur(0px)",
          borderBottom: "1px solid transparent",
          duration: 0.3,
          ease: "power2.out",
        });
      },
    });

    // Logo subtle glow on scroll
    if (logoRef.current) {
      ScrollTrigger.create({
        trigger: document.body,
        start: "top -100",
        onEnter: () => {
          gsap.to(logoRef.current, {
            filter: "drop-shadow(0 0 8px rgba(139, 92, 246, 0.4))",
            duration: 0.5,
            ease: "power2.out",
          });
        },
        onLeaveBack: () => {
          gsap.to(logoRef.current, {
            filter: "drop-shadow(0 0 0px rgba(139, 92, 246, 0))",
            duration: 0.5,
            ease: "power2.out",
          });
        },
      });
    }

    return () => {
      ScrollTrigger.getAll().forEach((trigger) => {
        if (
          trigger.vars.trigger === document.body ||
          trigger.vars.trigger === header
        ) {
          trigger.kill();
        }
      });
    };
  }, []);

  const navigation = [
    { name: "Features", href: "#features" },
    { name: "How It Works", href: "#how-it-works" },
    { name: "Pricing", href: "#pricing" },
    { name: "Testimonials", href: "#testimonials" },
  ];

  const handleNavClick = (
    e: React.MouseEvent<HTMLAnchorElement>,
    href: string,
  ) => {
    if (href.startsWith("#")) {
      e.preventDefault();
      const element = document.querySelector(href);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  };

  return (
    <header
      ref={headerRef}
      className="fixed top-0 left-0 right-0 w-full z-50 transition-all duration-300"
      style={{
        backgroundColor: isScrolled ? "var(--bg-glass)" : "transparent",
        backdropFilter: isScrolled ? "blur(24px)" : "none",
        WebkitBackdropFilter: isScrolled ? "blur(24px)" : "none",
        borderBottom: isScrolled ? "1px solid var(--border-subtle)" : "none",
      }}
    >
      <nav
        className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"
        aria-label="Main navigation"
      >
        <div className="flex items-center justify-between h-16 lg:h-20">
          <Link ref={logoRef} to="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-violet to-brand-violet-dark flex items-center justify-center">
              <span className="text-white font-bold text-lg">F</span>
            </div>
            <span
              className="text-xl font-bold"
              style={{ color: "var(--text-primary)" }}
            >
              Forge
            </span>
          </Link>

          <div className="hidden md:flex items-center space-x-8">
            {navigation.map((item) => (
              <a
                key={item.name}
                href={item.href}
                onClick={(e) => handleNavClick(e, item.href)}
                className="transition-colors duration-200 text-sm font-medium"
                style={{ color: "var(--text-secondary)" }}
                onMouseEnter={(e) => {
                  const target = e.currentTarget;
                  target.style.color = "var(--text-primary)";
                }}
                onMouseLeave={(e) => {
                  const target = e.currentTarget;
                  target.style.color = "var(--text-secondary)";
                }}
              >
                {item.name}
              </a>
            ))}
          </div>

          <div className="hidden md:flex items-center space-x-4">
            <ThemeToggle variant="icon" className="mr-2" />
            <button
              type="button"
              onClick={() => navigate("/auth/login")}
              className="px-4 py-2 text-sm font-medium transition-colors duration-200"
              style={{ color: "var(--text-secondary)" }}
              onMouseEnter={(e) => {
                const target = e.currentTarget;
                target.style.color = "var(--text-primary)";
              }}
              onMouseLeave={(e) => {
                const target = e.currentTarget;
                target.style.color = "var(--text-secondary)";
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => navigate("/auth/register")}
              className="px-6 py-2.5 bg-brand-violet hover:bg-brand-violet-dark text-white text-sm font-medium rounded-lg transition-all duration-200 shadow-glow hover:shadow-glow-lg"
            >
              Get Started
            </button>
          </div>

          <button
            type="button"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="lg:hidden p-2 transition-colors"
            style={{ color: "var(--text-secondary)" }}
            onMouseEnter={(e) => {
              const target = e.currentTarget;
              target.style.color = "var(--text-primary)";
            }}
            onMouseLeave={(e) => {
              const target = e.currentTarget;
              target.style.color = "var(--text-secondary)";
            }}
            aria-label="Toggle mobile menu"
          >
            {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {isMobileMenuOpen && (
          <div className="lg:hidden border-t border-border-subtle">
            <div className="px-2 pt-2 pb-3 space-y-1">
              {navigation.map((item) => (
                <a
                  key={item.name}
                  href={item.href}
                  onClick={(e) => {
                    handleNavClick(e, item.href);
                    setIsMobileMenuOpen(false);
                  }}
                  className="block px-3 py-2 text-base font-medium rounded-lg transition-all duration-200"
                  style={{
                    color: "var(--text-secondary)",
                  }}
                  onMouseEnter={(e) => {
                    const target = e.currentTarget;
                    target.style.color = "var(--text-primary)";
                    target.style.backgroundColor = "var(--bg-tertiary)";
                  }}
                  onMouseLeave={(e) => {
                    const target = e.currentTarget;
                    target.style.color = "var(--text-secondary)";
                    target.style.backgroundColor = "transparent";
                  }}
                >
                  {item.name}
                </a>
              ))}
              <div className="pt-4 space-y-2">
                <div className="flex items-center justify-center pb-2">
                  <ThemeToggle variant="icon" />
                </div>
                <button
                  type="button"
                  onClick={() => {
                    navigate("/auth/login");
                    setIsMobileMenuOpen(false);
                  }}
                  className="w-full px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200"
                  style={{ color: "var(--text-secondary)" }}
                  onMouseEnter={(e) => {
                    const target = e.currentTarget;
                    target.style.color = "var(--text-primary)";
                    target.style.backgroundColor = "var(--bg-tertiary)";
                  }}
                  onMouseLeave={(e) => {
                    const target = e.currentTarget;
                    target.style.color = "var(--text-secondary)";
                    target.style.backgroundColor = "transparent";
                  }}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  onClick={() => {
                    navigate("/auth/register");
                    setIsMobileMenuOpen(false);
                  }}
                  className="w-full px-6 py-2.5 bg-brand-violet hover:bg-brand-violet-dark text-white text-sm font-medium rounded-lg transition-all duration-200 shadow-glow"
                >
                  Get Started
                </button>
              </div>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}
