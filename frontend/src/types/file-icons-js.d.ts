declare module "file-icons-js" {
  interface FileIcons {
    getClass(filename: string): string;
    getClassWithColor(filename: string): string;
    db: any;
  }

  const fileIcons: FileIcons;
  export = fileIcons;
}

// Also allow require syntax
declare const fileIcons: {
  getClass(filename: string): string;
  getClassWithColor(filename: string): string;
  db: any;
};
