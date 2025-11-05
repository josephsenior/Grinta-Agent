export default function fixManifestPlugin() {
  return {
    name: 'fix-manifest',
    transformIndexHtml(html) {
      // Remove only the problematic manifest modulepreload
      return html.replace(
        /<link rel="modulepreload" href="\/assets\/manifest-[^"]+" \/>/g,
        ''
      );
    },
    transform(code, id) {
      // Remove only the problematic manifest import
      if (id.includes('index.html')) {
        return code.replace(/import\s+["']\/assets\/manifest-[^"']+["']\s*;?/g, '');
      }
      return code;
    }
  };
}
