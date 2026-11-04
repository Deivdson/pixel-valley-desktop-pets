"""
Construtor do Instalador Compacto (Self-Extracting .EXE + .ZIP Portátil)
do Pixel Valley Desktop Pets, incluindo todos os avatares já criados!

Otimizações de compactação aplicadas automaticamente no pacote:
- Remove arquivos temporários (__pycache__, .pyc, chaves de API);
- Inclui todos os avatares criados (spritesheets animadas 8x4, retratos de caixa de diálogo HD,
  retratos 64x64 e estado de amizade), omitindo apenas as imagens brutas source.jpg de ~2MB
  (ou comprimindo-as) para que o instalador final tenha menos de ~500 KB!
- Compila um instalador gráfico nativo do Windows (Instalador_Pixel_Valley_Pets.exe) com ícone,
  criação automática de atalhos na Área de Trabalho e Menu Iniciar, verificação de dependências
  e inicialização imediata.
"""

import os
import io
import zipfile
import subprocess
from typing import Tuple
from PIL import Image


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "instalador")

CODE_FILES = [
    "app.py",
    "desktop_pet.py",
    "dialogue_box.py",
    "gpt_luna.py",
    "library_manager.py",
    "llm_sprite_designer.py",
    "photo_analyzer.py",
    "sprite_generator.py",
    "spritesheet_importer.py",
    "Executar_Stardew_Pets.bat",
    "stardew_pet.ico",
    "README.md",
]

# Arquivos essenciais de cada avatar (exclui source.jpg de ~2MB que já foi compilado em spritesheet.png)
AVATAR_ESSENTIAL_FILES = {
    "avatar.json",
    "spritesheet.png",
    "portrait.png",
    "photo_portrait.png",
    "dialog_portrait.png",
    "dialogue_state.json",
}


def build_compact_payload_zip(include_compressed_sources: bool = False) -> Tuple[bytes, int, int]:
    """Cria o pacote ZIP em memória altamente compactado (LZMA/DEFLATED) com código + avatares."""
    buf = io.BytesIO()
    avatar_count = 0
    file_count = 0

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        # 1. Adicionar arquivos de código e recursos principais
        for fname in CODE_FILES:
            fpath = os.path.join(BASE_DIR, fname)
            if os.path.exists(fpath):
                zf.write(fpath, arcname=fname)
                file_count += 1

        # 2. Adicionar requirements.txt para instalação automática de dependências se necessário
        reqs = "Pillow>=10.0.0\nnumpy>=1.24.0\nhttpx>=0.24.0\n"
        zf.writestr("requirements.txt", reqs)
        file_count += 1

        # 3. Adicionar todos os avatares criados na biblioteca
        avatars_dir = os.path.join(BASE_DIR, "avatars")
        if os.path.exists(avatars_dir):
            for entry in sorted(os.listdir(avatars_dir)):
                av_folder = os.path.join(avatars_dir, entry)
                meta_file = os.path.join(av_folder, "avatar.json")
                if not (os.path.isdir(av_folder) and os.path.exists(meta_file)):
                    continue
                avatar_count += 1
                for item in sorted(os.listdir(av_folder)):
                    full_item = os.path.join(av_folder, item)
                    if not os.path.isfile(full_item):
                        continue
                    arc_path = f"avatars/{entry}/{item}"

                    if item in AVATAR_ESSENTIAL_FILES:
                        # Otimizar PNGs sem perda visual para máxima compactação
                        if item.endswith(".png"):
                            img = Image.open(full_item)
                            png_buf = io.BytesIO()
                            img.save(png_buf, format="PNG", optimize=True, compress_level=9)
                            zf.writestr(arc_path, png_buf.getvalue())
                        else:
                            zf.write(full_item, arcname=arc_path)
                        file_count += 1
                    elif include_compressed_sources and item.startswith("source."):
                        img = Image.open(full_item).convert("RGB")
                        jpg_buf = io.BytesIO()
                        img.save(jpg_buf, format="JPEG", quality=78, optimize=True)
                        zf.writestr(arc_path, jpg_buf.getvalue())
                        file_count += 1

    return buf.getvalue(), avatar_count, file_count


CSHARP_INSTALLER_SOURCE = r"""
using System;
using System.IO;
using System.IO.Compression;
using System.Diagnostics;
using System.Reflection;
using System.Windows.Forms;
using System.Drawing;

[assembly: AssemblyTitle("Instalador Pixel Valley Desktop Pets")]
[assembly: AssemblyDescription("Instalador Compacto com Avatares e Caixas de Dialogo")]
[assembly: AssemblyProduct("Pixel Valley Desktop Pets")]
[assembly: AssemblyVersion("4.2.0.0")]

namespace PixelValleyInstaller
{
    public class InstallerForm : Form
    {
        private TextBox txtPath;
        private CheckBox chkDesktopShortcut;
        private CheckBox chkLaunchNow;
        private CheckBox chkInstallDeps;
        private Button btnInstall;
        private ProgressBar progress;
        private Label lblStatus;

        public InstallerForm()
        {
            this.Text = "🌾 Instalador — Pixel Valley Desktop Pets (v4.2)";
            this.Size = new Size(560, 390);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(247, 226, 184);

            try {
                this.Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
            } catch {}

            Panel header = new Panel();
            header.Dock = DockStyle.Top;
            header.Height = 68;
            header.BackColor = Color.FromArgb(140, 74, 32);

            Label lblTitle = new Label();
            lblTitle.Text = "🌾 Pixel Valley Desktop Pets";
            lblTitle.Font = new Font("Segoe UI", 15, FontStyle.Bold);
            lblTitle.ForeColor = Color.FromArgb(255, 246, 224);
            lblTitle.Location = new Point(16, 10);
            lblTitle.AutoSize = true;
            header.Controls.Add(lblTitle);

            Label lblSub = new Label();
            lblSub.Text = "Instalador Compacto — Inclui Avatares Animados 4x6 & Caixas de Diálogo";
            lblSub.Font = new Font("Segoe UI", 9, FontStyle.Regular);
            lblSub.ForeColor = Color.FromArgb(245, 220, 180);
            lblSub.Location = new Point(18, 39);
            lblSub.AutoSize = true;
            header.Controls.Add(lblSub);

            this.Controls.Add(header);

            Label lblDir = new Label();
            lblDir.Text = "Pasta de Instalação:";
            lblDir.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            lblDir.ForeColor = Color.FromArgb(58, 30, 8);
            lblDir.Location = new Point(20, 84);
            lblDir.AutoSize = true;
            this.Controls.Add(lblDir);

            string defaultDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "PixelValleyDesktopPets"
            );

            txtPath = new TextBox();
            txtPath.Text = defaultDir;
            txtPath.Font = new Font("Segoe UI", 9);
            txtPath.Location = new Point(20, 106);
            txtPath.Size = new Size(410, 25);
            this.Controls.Add(txtPath);

            Button btnBrowse = new Button();
            btnBrowse.Text = "Procurar...";
            btnBrowse.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            btnBrowse.BackColor = Color.FromArgb(217, 130, 43);
            btnBrowse.ForeColor = Color.White;
            btnBrowse.FlatStyle = FlatStyle.Flat;
            btnBrowse.Location = new Point(438, 104);
            btnBrowse.Size = new Size(92, 27);
            btnBrowse.Click += (s, e) => {
                using (var fbd = new FolderBrowserDialog()) {
                    fbd.SelectedPath = txtPath.Text;
                    if (fbd.ShowDialog() == DialogResult.OK) {
                        txtPath.Text = fbd.SelectedPath;
                    }
                }
            };
            this.Controls.Add(btnBrowse);

            GroupBox grpInfo = new GroupBox();
            grpInfo.Text = "Pacote de Avatares Incluídos";
            grpInfo.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            grpInfo.ForeColor = Color.FromArgb(58, 30, 8);
            grpInfo.Location = new Point(20, 142);
            grpInfo.Size = new Size(510, 62);

            Label lblAvatars = new Label();
            lblAvatars.Text = "✔ Deivdson, Luzia, Larissa, Mateus, Analu, Dudu (Sprites 4x6 + Caixas de Diálogo HD)\n✔ Motor de Física na Barra de Tarefas + Editor Procedural + Atualizador Git";
            lblAvatars.Font = new Font("Segoe UI", 8.5f, FontStyle.Regular);
            lblAvatars.Location = new Point(12, 20);
            lblAvatars.Size = new Size(490, 36);
            grpInfo.Controls.Add(lblAvatars);
            this.Controls.Add(grpInfo);

            chkDesktopShortcut = new CheckBox();
            chkDesktopShortcut.Text = "Criar atalho na Área de Trabalho e no Menu Iniciar";
            chkDesktopShortcut.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            chkDesktopShortcut.ForeColor = Color.FromArgb(58, 30, 8);
            chkDesktopShortcut.Checked = true;
            chkDesktopShortcut.Location = new Point(22, 214);
            chkDesktopShortcut.AutoSize = true;
            this.Controls.Add(chkDesktopShortcut);

            chkInstallDeps = new CheckBox();
            chkInstallDeps.Text = "Verificar / instalar dependências Python automaticamente (Pillow, numpy, httpx)";
            chkInstallDeps.Font = new Font("Segoe UI", 9);
            chkInstallDeps.ForeColor = Color.FromArgb(58, 30, 8);
            chkInstallDeps.Checked = true;
            chkInstallDeps.Location = new Point(22, 238);
            chkInstallDeps.AutoSize = true;
            this.Controls.Add(chkInstallDeps);

            chkLaunchNow = new CheckBox();
            chkLaunchNow.Text = "Iniciar o Pixel Valley Desktop Pets ao concluir";
            chkLaunchNow.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            chkLaunchNow.ForeColor = Color.FromArgb(58, 30, 8);
            chkLaunchNow.Checked = true;
            chkLaunchNow.Location = new Point(22, 262);
            chkLaunchNow.AutoSize = true;
            this.Controls.Add(chkLaunchNow);

            progress = new ProgressBar();
            progress.Location = new Point(20, 292);
            progress.Size = new Size(340, 24);
            this.Controls.Add(progress);

            lblStatus = new Label();
            lblStatus.Text = "Pronto para instalar.";
            lblStatus.Font = new Font("Segoe UI", 8.5f, FontStyle.Italic);
            lblStatus.ForeColor = Color.FromArgb(90, 46, 20);
            lblStatus.Location = new Point(20, 320);
            lblStatus.AutoSize = true;
            this.Controls.Add(lblStatus);

            btnInstall = new Button();
            btnInstall.Text = "🚀 Instalar Agora";
            btnInstall.Font = new Font("Segoe UI", 10, FontStyle.Bold);
            btnInstall.BackColor = Color.FromArgb(62, 142, 76);
            btnInstall.ForeColor = Color.White;
            btnInstall.FlatStyle = FlatStyle.Flat;
            btnInstall.Location = new Point(372, 288);
            btnInstall.Size = new Size(158, 42);
            btnInstall.Cursor = Cursors.Hand;
            btnInstall.Click += OnInstallClick;
            this.Controls.Add(btnInstall);
        }

        private void OnInstallClick(object sender, EventArgs e)
        {
            string targetDir = txtPath.Text.Trim();
            if (string.IsNullOrEmpty(targetDir)) {
                MessageBox.Show("Escolha uma pasta válida.", "Aviso", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            btnInstall.Enabled = false;
            progress.Value = 15;
            lblStatus.Text = "Extraindo arquivos e avatares...";
            Application.DoEvents();

            try {
                if (!Directory.Exists(targetDir)) {
                    Directory.CreateDirectory(targetDir);
                }

                Assembly asm = Assembly.GetExecutingAssembly();
                using (Stream s = asm.GetManifestResourceStream("payload.zip")) {
                    if (s == null) {
                        throw new Exception("Pacote interno payload.zip não encontrado no executável.");
                    }
                    using (ZipArchive archive = new ZipArchive(s, ZipArchiveMode.Read)) {
                        int total = archive.Entries.Count;
                        int current = 0;
                        foreach (ZipArchiveEntry entry in archive.Entries) {
                            current++;
                            string fullPath = Path.Combine(targetDir, entry.FullName.Replace('/', Path.DirectorySeparatorChar));
                            string dirName = Path.GetDirectoryName(fullPath);
                            if (!string.IsNullOrEmpty(dirName) && !Directory.Exists(dirName)) {
                                Directory.CreateDirectory(dirName);
                            }
                            if (!string.IsNullOrEmpty(entry.Name)) {
                                entry.ExtractToFile(fullPath, true);
                            }
                            progress.Value = 15 + (int)(55.0 * current / Math.Max(1, total));
                            Application.DoEvents();
                        }
                    }
                }

                if (chkInstallDeps.Checked) {
                    lblStatus.Text = "Verificando bibliotecas Python (Pillow, numpy, httpx)...";
                    progress.Value = 75;
                    Application.DoEvents();
                    try {
                        ProcessStartInfo psi = new ProcessStartInfo("python", "-m pip install --quiet Pillow numpy httpx");
                        psi.WorkingDirectory = targetDir;
                        psi.WindowStyle = ProcessWindowStyle.Hidden;
                        psi.CreateNoWindow = true;
                        Process p = Process.Start(psi);
                        if (p != null) p.WaitForExit(25000);
                    } catch {}
                }

                if (chkDesktopShortcut.Checked) {
                    lblStatus.Text = "Criando atalhos na Área de Trabalho...";
                    progress.Value = 90;
                    Application.DoEvents();
                    CreateShortcut(
                        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "Pixel Valley Desktop Pets.lnk"),
                        Path.Combine(targetDir, "Executar_Stardew_Pets.bat"),
                        targetDir,
                        Path.Combine(targetDir, "stardew_pet.ico")
                    );
                    CreateShortcut(
                        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs), "Pixel Valley Desktop Pets.lnk"),
                        Path.Combine(targetDir, "Executar_Stardew_Pets.bat"),
                        targetDir,
                        Path.Combine(targetDir, "stardew_pet.ico")
                    );
                }

                progress.Value = 100;
                lblStatus.Text = "Instalação concluída com sucesso! 🎉";
                Application.DoEvents();

                if (chkLaunchNow.Checked) {
                    ProcessStartInfo startApp = new ProcessStartInfo();
                    startApp.FileName = Path.Combine(targetDir, "Executar_Stardew_Pets.bat");
                    startApp.WorkingDirectory = targetDir;
                    startApp.UseShellExecute = true;
                    Process.Start(startApp);
                } else {
                    MessageBox.Show(
                        "Pixel Valley Desktop Pets foi instalado em:\n" + targetDir,
                        "Instalação Concluída! 🌾",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Information
                    );
                }

                this.Close();
            }
            catch (Exception ex) {
                btnInstall.Enabled = true;
                lblStatus.Text = "Erro na instalação.";
                MessageBox.Show("Erro durante a instalação:\n" + ex.Message, "Erro", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void CreateShortcut(string shortcutPath, string targetFile, string workDir, string iconPath)
        {
            try {
                Type t = Type.GetTypeFromProgID("WScript.Shell");
                dynamic shell = Activator.CreateInstance(t);
                var lnk = shell.CreateShortcut(shortcutPath);
                lnk.TargetPath = targetFile;
                lnk.WorkingDirectory = workDir;
                if (File.Exists(iconPath)) {
                    lnk.IconLocation = iconPath;
                }
                lnk.Description = "Pixel Valley Desktop Pets - Bonequinhos e Caixas de Dialogo";
                lnk.Save();
            } catch {}
        }

        [STAThread]
        public static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new InstallerForm());
        }
    }
}
"""


def main():
    os.makedirs(DIST_DIR, exist_ok=True)

    # 1. Gerar pacote ZIP compacto (código + todos os avatares prontos)
    zip_bytes, av_count, f_count = build_compact_payload_zip(include_compressed_sources=False)
    zip_out_path = os.path.join(DIST_DIR, "Pixel_Valley_Desktop_Pets_Portatil.zip")
    with open(zip_out_path, "wb") as f:
        f.write(zip_bytes)

    # 2. Compilar instalador gráfico nativo do Windows (.EXE) com o payload.zip embutido
    payload_tmp = os.path.join(DIST_DIR, "payload.zip")
    cs_tmp = os.path.join(DIST_DIR, "Installer.cs")
    exe_out_path = os.path.join(DIST_DIR, "Instalador_Pixel_Valley_Pets.exe")
    ico_path = os.path.join(BASE_DIR, "stardew_pet.ico")

    with open(payload_tmp, "wb") as f:
        f.write(zip_bytes)
    with open(cs_tmp, "w", encoding="utf-8-sig") as f:
        f.write(CSHARP_INSTALLER_SOURCE)

    csc_path = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    if not os.path.exists(csc_path):
        csc_path = r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"

    cmd = [
        csc_path,
        "/target:winexe",
        "/optimize+",
        f"/out:{exe_out_path}",
        f"/resource:{payload_tmp},payload.zip",
        "/r:System.dll",
        "/r:System.Drawing.dll",
        "/r:System.Windows.Forms.dll",
        "/r:System.IO.Compression.dll",
        "/r:System.IO.Compression.FileSystem.dll",
        "/r:Microsoft.CSharp.dll",
    ]
    if os.path.exists(ico_path):
        cmd.append(f"/win32icon:{ico_path}")
    cmd.append(cs_tmp)

    res = subprocess.run(cmd, capture_output=True, text=True)
    # Limpar temporários de compilação
    for tmp in (payload_tmp, cs_tmp):
        if os.path.exists(tmp):
            os.remove(tmp)

    if res.returncode != 0:
        raise RuntimeError(f"Erro ao compilar instalador .EXE:\n{res.stdout}\n{res.stderr}")

    exe_kb = os.path.getsize(exe_out_path) / 1024.0
    zip_kb = os.path.getsize(zip_out_path) / 1024.0
    print(f"Avatares empacotados: {av_count} ({f_count} arquivos)")
    print(f"Instalador EXE gerado: {exe_out_path} ({exe_kb:.1f} KB)")
    print(f"Pacote ZIP Portatil : {zip_out_path} ({zip_kb:.1f} KB)")


if __name__ == "__main__":
    main()
