package co.sidrahomes.staff;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Message;
import android.webkit.*;
import android.widget.*;
import java.net.HttpURLConnection;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.net.URI;

/** Tiny system-WebView shell. ERP data, authentication and business rules stay on the server. */
public final class MainActivity extends Activity {
    private WebView web;
    private TextView status;
    private String origin;
    private ValueCallback<Uri[]> fileCallback;
    private GeolocationPermissions.Callback geoCallback;
    private String geoOrigin;
    private String pendingDownload;
    private boolean clearHistory;
    private final ExecutorService io = Executors.newSingleThreadExecutor();

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
        root.setOnApplyWindowInsetsListener((v, insets) -> {v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());return insets;});
        LinearLayout bar = new LinearLayout(this); bar.setPadding(12,4,12,4); bar.setBackgroundColor(Color.rgb(23,59,50));
        status = new TextView(this);status.setText("SIDRA HOMES");status.setTextColor(Color.WHITE);status.setPadding(8,16,8,16);
        Button reload = new Button(this);reload.setText("↻");reload.setContentDescription("Reload");reload.setOnClickListener(v -> web.reload());
        Button server = new Button(this);server.setText("Server");server.setOnClickListener(v -> configure());
        bar.addView(status,new LinearLayout.LayoutParams(0,-2,1));bar.addView(reload);bar.addView(server);root.addView(bar);
        web = new WebView(this);root.addView(web,new LinearLayout.LayoutParams(-1,0,1));setContentView(root);
        WebSettings s=web.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setAllowFileAccess(false);s.setAllowContentAccess(true);s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);s.setGeolocationEnabled(true);s.setSupportMultipleWindows(true);s.setJavaScriptCanOpenWindowsAutomatically(false);
        CookieManager.getInstance().setAcceptCookie(true);CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request){
                Uri uri=request.getUrl();if(sameOrigin(uri.toString()))return false;
                if(request.hasGesture() && "https".equals(uri.getScheme()))startActivity(new Intent(Intent.ACTION_VIEW,uri));
                return true;
            }
            @Override public void onReceivedError(WebView view,WebResourceRequest request,WebResourceError error){if(request.isForMainFrame())status.setText("Offline · retry with ↻");}
            @Override public void onPageFinished(WebView view,String url){status.setText("SIDRA HOMES");if(clearHistory){web.clearHistory();clearHistory=false;}CookieManager.getInstance().flush();}
            // Default WebView behavior cancels certificate errors; no bypass is provided.
        });
        web.setWebChromeClient(new WebChromeClient(){
            @Override public boolean onCreateWindow(WebView view,boolean dialog,boolean userGesture,Message result){
                if(!userGesture)return false;
                WebView popup=new WebView(MainActivity.this);
                popup.setWebViewClient(new WebViewClient(){
                    @Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest request){
                        String url=request.getUrl().toString();
                        if(url.equals("about:blank"))return false;
                        if(sameOrigin(url))web.loadUrl(url);
                        else if("https".equals(request.getUrl().getScheme()))startActivity(new Intent(Intent.ACTION_VIEW,request.getUrl()));
                        popup.destroy();return true;
                    }
                });
                ((WebView.WebViewTransport)result.obj).setWebView(popup);result.sendToTarget();return true;
            }
            @Override public boolean onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params){
                if(fileCallback!=null)fileCallback.onReceiveValue(null);fileCallback=callback;
                try{startActivityForResult(params.createIntent(),41);return true;}catch(Exception error){fileCallback=null;callback.onReceiveValue(null);return true;}
            }
            @Override public void onGeolocationPermissionsShowPrompt(String requestedOrigin,GeolocationPermissions.Callback callback){
                if(!sameOrigin(requestedOrigin)){callback.invoke(requestedOrigin,false,false);return;}
                if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED || checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)==PackageManager.PERMISSION_GRANTED){callback.invoke(requestedOrigin,true,false);return;}
                if(geoCallback!=null)geoCallback.invoke(geoOrigin,false,false);
                geoOrigin=requestedOrigin;geoCallback=callback;
                requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION},42);
            }
        });
        web.setDownloadListener((url,ua,disposition,mime,length) -> {
            if(!sameOrigin(url)){Toast.makeText(this,"Downloads must belong to the configured server.",Toast.LENGTH_LONG).show();return;}
            pendingDownload=url;Intent save=new Intent(Intent.ACTION_CREATE_DOCUMENT);save.addCategory(Intent.CATEGORY_OPENABLE);save.setType(mime==null?"application/octet-stream":mime);save.putExtra(Intent.EXTRA_TITLE,URLUtil.guessFileName(url,disposition,mime));startActivityForResult(save,43);
        });
        origin=getPreferences(MODE_PRIVATE).getString("server",null);
        if(origin==null)configure();else open();
    }
    private boolean sameOrigin(String value){
        try{URI u=new URI(value),base=new URI(origin==null?"https://invalid.invalid":origin);return "https".equalsIgnoreCase(u.getScheme())&&u.getUserInfo()==null&&base.getHost().equalsIgnoreCase(u.getHost())&&port(base)==port(u);}catch(Exception error){return false;}
    }
    private static int port(URI u){return u.getPort()==-1?443:u.getPort();}
    private String validate(String value) throws Exception {
        URI u=new URI(value.trim());String path=u.getPath();
        if(!"https".equalsIgnoreCase(u.getScheme())||u.getHost()==null||u.getUserInfo()!=null||u.getQuery()!=null||u.getFragment()!=null||!(path==null||path.isEmpty()||path.equals("/")))throw new Exception();
        return "https://"+u.getRawAuthority();
    }
    private void configure(){
        EditText input=new EditText(this);input.setSingleLine();input.setHint("https://your-sidra-server");input.setText(origin==null?"":origin);input.setInputType(17);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Connect to Sidra").setMessage("Enter the HTTPS server address provided by your administrator.").setView(input).setPositiveButton("Connect",null).setNegativeButton("Cancel",null).create();
        dialog.setOnShowListener(v -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(button -> {
            try{String next=validate(input.getText().toString());
                boolean changed=!next.equals(origin);web.stopLoading();
                origin=next;getPreferences(MODE_PRIVATE).edit().putString("server",origin).apply();dialog.dismiss();
                if(changed){WebStorage.getInstance().deleteAllData();web.clearHistory();clearHistory=true;web.clearCache(true);CookieManager.getInstance().removeAllCookies(done -> open());}
                else open();
            }catch(Exception error){input.setError("Use an HTTPS address without a path or credentials.");}
        }));dialog.show();
    }
    private void open(){web.loadUrl(origin+"/sidra-staff/");}
    @Override protected void onActivityResult(int request,int result,Intent intent){
        super.onActivityResult(request,result,intent);
        if(request==41&&fileCallback!=null){fileCallback.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(result,intent));fileCallback=null;}
        if(request==43 && pendingDownload!=null){String url=pendingDownload;pendingDownload=null;if(result!=RESULT_OK || intent==null || intent.getData()==null)return;Uri destination=intent.getData();String cookie=CookieManager.getInstance().getCookie(url);
            io.execute(() -> {HttpURLConnection connection=null;
                try{if(!sameOrigin(url))throw new Exception("Server changed");connection=(HttpURLConnection)new URI(url).toURL().openConnection();connection.setInstanceFollowRedirects(false);connection.setConnectTimeout(15000);connection.setReadTimeout(30000);if(cookie!=null)connection.setRequestProperty("Cookie",cookie);if(connection.getResponseCode()!=200)throw new Exception("Download refused");
                    try(InputStream in=connection.getInputStream();OutputStream out=getContentResolver().openOutputStream(destination)){if(out==null)throw new Exception("Destination unavailable");byte[] buffer=new byte[16384];int n;while((n=in.read(buffer))!=-1)out.write(buffer,0,n);}
                    runOnUiThread(() -> Toast.makeText(this,"File saved",Toast.LENGTH_SHORT).show());
                }catch(Exception error){runOnUiThread(() -> Toast.makeText(this,"Download failed. Sign in again and retry.",Toast.LENGTH_LONG).show());}
                finally{if(connection!=null)connection.disconnect();}
            });
        }
    }
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] results){super.onRequestPermissionsResult(request,permissions,results);if(request==42&&geoCallback!=null){boolean allowed=false;for(int r:results)allowed|=r==PackageManager.PERMISSION_GRANTED;geoCallback.invoke(geoOrigin,allowed,false);geoCallback=null;}}
    @Override public void onBackPressed(){if(web.canGoBack())web.goBack();else super.onBackPressed();}
    @Override protected void onDestroy(){if(fileCallback!=null)fileCallback.onReceiveValue(null);if(geoCallback!=null)geoCallback.invoke(geoOrigin,false,false);io.shutdownNow();web.destroy();super.onDestroy();}
}
