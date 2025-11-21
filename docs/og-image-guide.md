# Open Graph Image Guide

## Current Implementation

We've created an SVG Open Graph image at `/public/forge-og-image.svg` that matches Forge's branding:
- **Size**: 1200x630px (recommended OG image size)
- **Format**: SVG (scalable, works on modern platforms)
- **Design**: Black background with violet gradient accents matching Forge branding

## Converting to PNG (Optional)

Some social media platforms prefer PNG images. To convert the SVG to PNG:

### Option 1: Using Node.js (Recommended)

```bash
# Install sharp (if not already installed)
npm install --save-dev sharp

# Create a conversion script
node scripts/convert-og-image.js
```

### Option 2: Using Online Tools

1. Open `frontend/public/forge-og-image.svg` in a browser
2. Use browser DevTools to take a screenshot at 1200x630px
3. Save as `frontend/public/forge-og-image.png`

### Option 3: Using ImageMagick

```bash
# Install ImageMagick first
convert -background black -density 300 forge-og-image.svg -resize 1200x630 forge-og-image.png
```

### Option 4: Using Inkscape

```bash
inkscape forge-og-image.svg --export-filename=forge-og-image.png --export-width=1200 --export-height=630
```

## Testing Your OG Image

### Facebook/LinkedIn Debugger
- Facebook: https://developers.facebook.com/tools/debug/
- LinkedIn: https://www.linkedin.com/post-inspector/

### Twitter Card Validator
- Twitter: https://cards-dev.twitter.com/validator

### General OG Validator
- OpenGraph.xyz: https://www.opengraph.xyz/

## Customizing the Image

The SVG file is located at `frontend/public/forge-og-image.svg`. You can edit it to:
- Change colors
- Update tagline
- Add logo
- Modify layout

## Platform-Specific Notes

- **Facebook/LinkedIn**: Prefer PNG, but SVG works
- **Twitter**: Supports both SVG and PNG
- **Discord**: Works with both formats
- **Slack**: Prefers PNG

## Current Status

✅ SVG image created at `/public/forge-og-image.svg`
✅ SEO component configured to use the image
✅ Default OG image set in SEO component

**Next Step (Optional)**: Convert to PNG for maximum compatibility if needed.

