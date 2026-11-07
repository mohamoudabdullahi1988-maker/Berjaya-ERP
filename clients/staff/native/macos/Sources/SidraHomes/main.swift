import AppKit
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    var window: NSWindow!
    var web: WKWebView!
    var origin: URL?
    func applicationDidFinishLaunching(_ notification: Notification) {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = self; web.uiDelegate = self
        web.allowsBackForwardNavigationGestures = true
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1280, height: 850), styleMask: [.titled,.closable,.miniaturizable,.resizable], backing: .buffered, defer: false)
        window.title = "Sidra Homes"
        let root = NSStackView(); root.orientation = .vertical; root.spacing = 0; root.distribution = .fill
        web.setContentHuggingPriority(NSLayoutConstraint.Priority(1), for: .vertical)
        let buttons = NSStackView(); buttons.orientation = .horizontal; buttons.spacing = 12
        buttons.edgeInsets = NSEdgeInsets(top: 8, left: 14, bottom: 8, right: 14)
        buttons.addArrangedSubview(NSButton(title: "Server…", target: self, action: #selector(configure)))
        buttons.addArrangedSubview(NSButton(title: "Reload", target: self, action: #selector(reload)))
        root.addArrangedSubview(buttons); root.addArrangedSubview(web)
        web.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        window.contentView = root; window.center(); window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        if let text = UserDefaults.standard.string(forKey: "server"), let value = validate(text) { origin = value; openPortal() }
        else { configure() }
    }
    func validate(_ text: String) -> URL? {
        guard let c = URLComponents(string: text.trimmingCharacters(in: .whitespacesAndNewlines)), c.scheme?.lowercased() == "https", let host = c.host, !host.isEmpty, c.user == nil, c.password == nil, c.query == nil, c.fragment == nil, c.path.isEmpty || c.path == "/" else { return nil }
        var clean = c; clean.path = ""; return clean.url
    }
    func sameOrigin(_ url: URL) -> Bool {
        guard let base = origin else { return false }
        return url.scheme?.lowercased() == "https" && url.user == nil && url.password == nil && url.host?.lowercased() == base.host?.lowercased() && (url.port ?? 443) == (base.port ?? 443)
    }
    @objc func configure() {
        let alert = NSAlert(); alert.messageText = "Connect to Sidra"
        alert.informativeText = "Enter the HTTPS test or production server address supplied by your administrator."
        let input = NSTextField(frame: NSRect(x: 0, y: 0, width: 360, height: 26)); input.stringValue = origin?.absoluteString ?? ""; input.placeholderString = "https://your-sidra-server"
        alert.accessoryView = input; alert.addButton(withTitle: "Connect"); alert.addButton(withTitle: "Cancel")
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        guard let next = validate(input.stringValue) else { showError("Use an HTTPS address without credentials, a path, query or fragment."); return }
        let changed = next != origin; origin = next; UserDefaults.standard.set(next.absoluteString, forKey: "server")
        if changed {
            web.stopLoading()
            WKWebsiteDataStore.default().removeData(ofTypes: WKWebsiteDataStore.allWebsiteDataTypes(), modifiedSince: .distantPast) { [weak self] in
                DispatchQueue.main.async { self?.web.loadHTMLString("", baseURL: nil); self?.openPortal() }
            }
        } else { openPortal() }
    }
    func openPortal() { if let base = origin { web.load(URLRequest(url: base.appendingPathComponent("sidra-staff/"))) } }
    @objc func reload() { web.reload() }
    func showError(_ message: String) { let a = NSAlert(); a.messageText = "Sidra Homes"; a.informativeText = message; a.runModal() }
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else { decisionHandler(.cancel); return }
        if url.absoluteString == "about:blank" { decisionHandler(.allow); return }
        if sameOrigin(url) { decisionHandler(.allow); return }
        if navigationAction.navigationType == .linkActivated && url.scheme == "https" { NSWorkspace.shared.open(url) }
        decisionHandler(.cancel)
    }
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        guard let url = navigationAction.request.url else { return nil }
        if sameOrigin(url) { webView.load(navigationAction.request) }
        else if url.scheme == "https", navigationAction.navigationType == .linkActivated { NSWorkspace.shared.open(url) }
        return nil
    }
    func webView(_ webView: WKWebView, decidePolicyFor navigationResponse: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        guard let url = navigationResponse.response.url, sameOrigin(url) else { decisionHandler(.cancel); return }
        let attachment = (navigationResponse.response as? HTTPURLResponse)?.value(forHTTPHeaderField: "Content-Disposition")?.lowercased().contains("attachment") ?? false
        decisionHandler(attachment || !navigationResponse.canShowMIMEType ? .download : .allow)
    }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { download.delegate = self }
    func download(_ download: WKDownload, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, decisionHandler: @escaping (WKDownload.RedirectPolicy) -> Void) {
        decisionHandler(request.url.map { sameOrigin($0) } == true ? .allow : .cancel)
    }
    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        let panel = NSSavePanel(); panel.nameFieldStringValue = (suggestedFilename as NSString).lastPathComponent
        panel.beginSheetModal(for: window) { result in completionHandler(result == .OK ? panel.url : nil) }
    }
    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        let panel = NSOpenPanel(); panel.allowsMultipleSelection = parameters.allowsMultipleSelection; panel.canChooseDirectories = parameters.allowsDirectories
        panel.beginSheetModal(for: window) { result in completionHandler(result == .OK ? panel.urls : nil) }
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { showError("The server could not be reached. Check your connection, then choose Reload.") }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
