import { Link } from "react-router-dom";
import { Home, ArrowLeft } from "lucide-react";
import { Button } from "#/components/ui/button";

export default function NotFound() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-black text-foreground">
      <div className="relative z-[1] flex min-h-screen flex-col items-center justify-center px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          {/* 404 Number */}
          <div className="mb-8">
            <h1 className="text-9xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-brand-500 via-accent-500 to-brand-600">
              404
            </h1>
          </div>

          {/* Error Message */}
          <div className="mb-8 space-y-4">
            <h2 className="text-3xl font-semibold text-white sm:text-4xl">
              Page Not Found
            </h2>
            <p className="text-lg text-white/70">
              The page you're looking for doesn't exist or has been moved.
            </p>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              asChild
              className="bg-white text-black hover:bg-white/90 font-semibold rounded-xl px-6 py-3"
            >
              <Link to="/">
                <Home className="mr-2 h-4 w-4" />
                Go Home
              </Link>
            </Button>
            <Button
              variant="outline"
              onClick={() => window.history.back()}
              className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Go Back
            </Button>
          </div>

          {/* Quick Links */}
          <div className="mt-12 pt-8 border-t border-white/10">
            <p className="text-sm text-white/60 mb-4">Popular Pages:</p>
            <div className="flex flex-wrap items-center justify-center gap-4">
              <Link
                to="/"
                className="text-sm text-white/80 hover:text-white transition-colors"
              >
                Home
              </Link>
              <span className="text-white/20">•</span>
              <Link
                to="/about"
                className="text-sm text-white/80 hover:text-white transition-colors"
              >
                About
              </Link>
              <span className="text-white/20">•</span>
              <Link
                to="/pricing"
                className="text-sm text-white/80 hover:text-white transition-colors"
              >
                Pricing
              </Link>
              <span className="text-white/20">•</span>
              <Link
                to="/settings"
                className="text-sm text-white/80 hover:text-white transition-colors"
              >
                Settings
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
