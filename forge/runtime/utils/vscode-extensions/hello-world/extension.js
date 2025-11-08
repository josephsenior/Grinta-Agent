const vscode = require('vscode');

function activate(context) {
  let disposable = vscode.commands.registerCommand('Forge-hello-world.helloWorld', function () {
    vscode.window.showInformationMessage('Hello from Forge!');
  });

  context.subscriptions.push(disposable);
}

function deactivate() {}

module.exports = {
  activate,
  deactivate,
};
