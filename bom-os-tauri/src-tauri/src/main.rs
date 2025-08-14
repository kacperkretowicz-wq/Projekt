
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{AppHandle, Manager};

#[tauri::command]
fn ping() -> String {
  "pong".into()
}

fn main() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .invoke_handler(tauri::generate_handler![ping])
    .setup(|app| {
      // DEV: uruchom Flask z systemowego Pythona (http://127.0.0.1:5005)
      #[cfg(debug_assertions)]
      {
        let app_dir = app.path().app_data_dir().unwrap();
        let _ = std::fs::create_dir_all(&app_dir);
        let py = if cfg!(target_os = "windows") { "python" } else { "python3" };
        let cmd = tauri::api::process::Command::new_sidecar(py)
          .expect("python not found")
          .args(["pyserver/app.py"])
          .spawn()
          .expect("failed to spawn flask sidecar");
        app.manage(cmd);
      }

      // PROD: jeżeli istnieje zbudowany sidecar (PyInstaller), uruchom go
      #[cfg(not(debug_assertions))]
      {
        if let Ok(cmd) = tauri::api::process::Command::new_sidecar("flask_sidecar") {
          let handle = cmd.spawn().expect("failed to spawn flask sidecar");
          app.manage(handle);
        }
      }

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
