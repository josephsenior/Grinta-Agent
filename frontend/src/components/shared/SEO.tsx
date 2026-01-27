import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export interface SEOProps {
  title?: string;
  description?: string;
  keywords?: string;
  ogTitle?: string;
  ogDescription?: string;
  ogImage?: string;
  ogType?: "website" | "article" | "profile";
  ogUrl?: string;
  twitterCard?: "summary" | "summary_large_image" | "app" | "player";
  twitterTitle?: string;
  twitterDescription?: string;
  twitterImage?: string;
  canonicalUrl?: string;
  noindex?: boolean;
  nofollow?: boolean;
}

const DEFAULT_TITLE = "Forge - AI Development Platform";
const DEFAULT_DESCRIPTION =
  "Build software faster with Forge, the AI-powered development platform. Advanced agents, real-time collaboration, and intelligent code generation.";
const DEFAULT_OG_IMAGE = "/forge-og-image.svg"; // SVG OG image (can be converted to PNG if needed)
const BASE_URL = typeof window !== "undefined" ? window.location.origin : "";

// Helper functions for meta tag operations
function updateMetaTag(name: string, content: string, property = false): void {
  const attribute = property ? "property" : "name";
  let element = document.querySelector(
    `meta[${attribute}="${name}"]`,
  ) as HTMLMetaElement;

  if (!element) {
    element = document.createElement("meta");
    element.setAttribute(attribute, name);
    document.head.appendChild(element);
  }

  element.setAttribute("content", content);
}

function removeMetaTag(name: string, property = false): void {
  const attribute = property ? "property" : "name";
  const element = document.querySelector(`meta[${attribute}="${name}"]`);
  if (element) {
    element.remove();
  }
}

function updateCanonicalUrl(url: string | null): void {
  if (url) {
    let canonical = document.querySelector(
      "link[rel='canonical']",
    ) as HTMLLinkElement;
    if (!canonical) {
      canonical = document.createElement("link");
      canonical.setAttribute("rel", "canonical");
      document.head.appendChild(canonical);
    }
    canonical.setAttribute("href", url);
  } else {
    const canonical = document.querySelector("link[rel='canonical']");
    if (canonical) {
      canonical.remove();
    }
  }
}

// Hook for basic meta tags (description, keywords, robots)
function useBasicMetaTags(
  description?: string,
  keywords?: string,
  noindex?: boolean,
  nofollow?: boolean,
): void {
  useEffect(() => {
    updateMetaTag("description", description || DEFAULT_DESCRIPTION);

    if (keywords) {
      updateMetaTag("keywords", keywords);
    } else {
      removeMetaTag("keywords");
    }

    if (noindex || nofollow) {
      const robotsContent = [
        noindex ? "noindex" : "",
        nofollow ? "nofollow" : "",
      ]
        .filter(Boolean)
        .join(", ");
      updateMetaTag("robots", robotsContent);
    } else {
      removeMetaTag("robots");
    }

    return () => {
      updateMetaTag("description", DEFAULT_DESCRIPTION);
      removeMetaTag("keywords");
      removeMetaTag("robots");
    };
  }, [description, keywords, noindex, nofollow]);
}

// Hook for Open Graph tags
function useOpenGraphTags(
  ogTitle?: string,
  ogDescription?: string,
  ogImage?: string,
  ogType?: "website" | "article" | "profile",
  ogUrl?: string,
  title?: string,
  description?: string,
  pathname?: string,
): void {
  useEffect(() => {
    const titleValue = ogTitle || title || DEFAULT_TITLE;
    const descriptionValue =
      ogDescription || description || DEFAULT_DESCRIPTION;
    const imageValue = ogImage || `${BASE_URL}${DEFAULT_OG_IMAGE}`;
    const urlValue = ogUrl || `${BASE_URL}${pathname || ""}`;

    updateMetaTag("og:title", titleValue, true);
    updateMetaTag("og:description", descriptionValue, true);
    updateMetaTag("og:type", ogType || "website", true);
    updateMetaTag("og:image", imageValue, true);
    updateMetaTag("og:url", urlValue, true);
    updateMetaTag("og:site_name", "Forge", true);

    return () => {
      updateMetaTag("og:title", DEFAULT_TITLE, true);
      updateMetaTag("og:description", DEFAULT_DESCRIPTION, true);
      updateMetaTag("og:type", "website", true);
      updateMetaTag("og:image", `${BASE_URL}${DEFAULT_OG_IMAGE}`, true);
      updateMetaTag("og:url", BASE_URL, true);
    };
  }, [
    ogTitle,
    ogDescription,
    ogImage,
    ogType,
    ogUrl,
    title,
    description,
    pathname,
  ]);
}

// Hook for Twitter Card tags
function useTwitterTags(
  twitterCard?: "summary" | "summary_large_image" | "app" | "player",
  twitterTitle?: string,
  twitterDescription?: string,
  twitterImage?: string,
  ogTitle?: string,
  ogDescription?: string,
  ogImage?: string,
  title?: string,
  description?: string,
): void {
  useEffect(() => {
    const titleValue = twitterTitle || ogTitle || title || DEFAULT_TITLE;
    const descriptionValue =
      twitterDescription || ogDescription || description || DEFAULT_DESCRIPTION;
    const imageValue =
      twitterImage || ogImage || `${BASE_URL}${DEFAULT_OG_IMAGE}`;

    updateMetaTag("twitter:card", twitterCard || "summary_large_image");
    updateMetaTag("twitter:title", titleValue);
    updateMetaTag("twitter:description", descriptionValue);
    updateMetaTag("twitter:image", imageValue);

    return () => {
      updateMetaTag("twitter:card", "summary_large_image");
      updateMetaTag("twitter:title", DEFAULT_TITLE);
      updateMetaTag("twitter:description", DEFAULT_DESCRIPTION);
      updateMetaTag("twitter:image", `${BASE_URL}${DEFAULT_OG_IMAGE}`);
    };
  }, [
    twitterCard,
    twitterTitle,
    twitterDescription,
    twitterImage,
    ogTitle,
    ogDescription,
    ogImage,
    title,
    description,
  ]);
}

// Hook for document title
function useDocumentTitle(title?: string): void {
  useEffect(() => {
    const fullTitle = title ? `${title} | Forge` : DEFAULT_TITLE;
    document.title = fullTitle;

    return () => {
      document.title = DEFAULT_TITLE;
    };
  }, [title]);
}

// Hook for canonical URL
function useCanonicalUrl(canonicalUrl?: string, pathname?: string): void {
  useEffect(() => {
    const url = canonicalUrl || (pathname ? `${BASE_URL}${pathname}` : null);
    updateCanonicalUrl(url);

    return () => {
      updateCanonicalUrl(null);
    };
  }, [canonicalUrl, pathname]);
}

/**
 * SEO Component - Dynamically updates meta tags for better SEO and social sharing
 *
 * Usage:
 * ```tsx
 * <SEO
 *   title="Dashboard - Forge"
 *   description="Manage your AI development projects"
 *   ogImage="/dashboard-preview.png"
 * />
 * ```
 */
export function SEO({
  title,
  description,
  keywords,
  ogTitle,
  ogDescription,
  ogImage,
  ogType = "website",
  ogUrl,
  twitterCard = "summary_large_image",
  twitterTitle,
  twitterDescription,
  twitterImage,
  canonicalUrl,
  noindex = false,
  nofollow = false,
}: SEOProps) {
  const location = useLocation();

  // Use separate hooks for different tag types
  useDocumentTitle(title);
  useBasicMetaTags(description, keywords, noindex, nofollow);
  useOpenGraphTags(
    ogTitle,
    ogDescription,
    ogImage,
    ogType,
    ogUrl,
    title,
    description,
    location.pathname,
  );
  useTwitterTags(
    twitterCard,
    twitterTitle,
    twitterDescription,
    twitterImage,
    ogTitle,
    ogDescription,
    ogImage,
    title,
    description,
  );
  useCanonicalUrl(canonicalUrl, location.pathname);

  // This component doesn't render anything
  return null;
}

/**
 * Hook version of SEO component for use in functional components
 *
 * Usage:
 * ```tsx
 * useSEO({
 *   title: "Dashboard",
 *   description: "Manage your projects"
 * });
 * ```
 */
export function useSEO(props: SEOProps) {
  const location = useLocation();
  const {
    title,
    description,
    keywords,
    ogTitle,
    ogDescription,
    ogImage,
    ogType,
    ogUrl,
    twitterCard,
    twitterTitle,
    twitterDescription,
    twitterImage,
    canonicalUrl,
    noindex,
    nofollow,
  } = props;

  useDocumentTitle(title);
  useBasicMetaTags(description, keywords, noindex, nofollow);
  useOpenGraphTags(
    ogTitle,
    ogDescription,
    ogImage,
    ogType,
    ogUrl,
    title,
    description,
    location.pathname,
  );
  useTwitterTags(
    twitterCard,
    twitterTitle,
    twitterDescription,
    twitterImage,
    ogTitle,
    ogDescription,
    ogImage,
    title,
    description,
  );
  useCanonicalUrl(canonicalUrl, location.pathname);
}
