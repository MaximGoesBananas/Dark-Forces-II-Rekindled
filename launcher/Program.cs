using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Drawing.Text;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using System.Windows.Forms;
using Microsoft.Win32;

namespace ModLauncher
{
    sealed class ActionButton : Button
    {
        protected override void OnPaint(PaintEventArgs e)
        {
            if (Enabled) { base.OnPaint(e); return; }
            e.Graphics.Clear(BackColor);
            using (var pen = new Pen(FlatAppearance.BorderColor)) e.Graphics.DrawRectangle(pen, 0, 0, Width - 1, Height - 1);
            TextRenderer.DrawText(e.Graphics, Text, Font, ClientRectangle, Color.Gray, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
        }
    }
    public sealed class LauncherForm : Form
    {
        readonly Installer installer;
        readonly TextBox folder = new TextBox();
        readonly Label status = new Label();
        readonly ProgressBar progress = new ProgressBar();
        readonly Button install = new ActionButton(), play = new ActionButton(), remove = new ActionButton(), browse = new ActionButton();
        readonly string preference = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Jedi Knight RPG", "game-folder.txt");
        readonly Color gold = Color.FromArgb(228, 180, 83);
        readonly PrivateFontCollection displayFonts = new PrivateFontCollection();
        IntPtr fontMemory, fontHandle;
        [DllImport("gdi32.dll")] static extern IntPtr AddFontMemResourceEx(IntPtr data, uint length, IntPtr reserved, ref uint count);
        [DllImport("gdi32.dll")] static extern bool RemoveFontMemResourceEx(IntPtr handle);
        bool busy;

        public LauncherForm(Installer package)
        {
            installer = package;
            using (var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("Orbitron.ttf"))
            using (var data = new MemoryStream()) {
                stream.CopyTo(data);
                byte[] bytes = data.ToArray();
                fontMemory = Marshal.AllocCoTaskMem(bytes.Length);
                Marshal.Copy(bytes, 0, fontMemory, bytes.Length);
                displayFonts.AddMemoryFont(fontMemory, bytes.Length);
                uint count = 0;
                fontHandle = AddFontMemResourceEx(fontMemory, (uint)bytes.Length, IntPtr.Zero, ref count);
            }
            Disposed += delegate {
                displayFonts.Dispose();
                if (fontHandle != IntPtr.Zero) RemoveFontMemResourceEx(fontHandle);
                Marshal.FreeCoTaskMem(fontMemory);
            };
            Text = "Rekindled";
            ShowIcon = false;
            ClientSize = new Size(760, 595);
            AutoScroll = true;
            StartPosition = FormStartPosition.CenterScreen;
            Font = new Font("Segoe UI", 10);
            BackColor = Color.FromArgb(20, 22, 25);
            ForeColor = Color.FromArgb(231, 229, 222);
            AutoScaleMode = AutoScaleMode.Dpi;
            AutoScaleDimensions = new SizeF(96, 96);
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            AddLabel("STAR WARS JEDI KNIGHT: DARK FORCES II", 32, 18, 696, 25, 10, gold, true);
            AddLabel("REKINDLED", 27, 40, 540, 64, 34, ForeColor, true);
            var poster = new PictureBox { Left = 32, Top = 110, Width = 696, Height = 218,
                SizeMode = PictureBoxSizeMode.Zoom, AccessibleName = "Rekindled gameplay and upgrades" };
            using (var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("poster.jpg"))
            using (var image = Image.FromStream(stream)) poster.Image = new Bitmap(image);
            Controls.Add(poster);
            Disposed += delegate { poster.Image.Dispose(); };
            AddLabel("Jedi Knight game folder", 32, 348, 696, 25, 10, ForeColor);
            folder.SetBounds(32, 379, 568, 30);
            folder.AccessibleName = "Jedi Knight game folder";
            folder.BackColor = Color.FromArgb(33, 36, 40); folder.ForeColor = ForeColor;
            folder.BorderStyle = BorderStyle.FixedSingle;
            folder.TextChanged += delegate { RefreshState(); };
            Controls.Add(folder);
            SetupButton(browse, "Browse...", 616, 374, 112, delegate {
                using (var dialog = new FolderBrowserDialog { Description = "Choose your Jedi Knight: Dark Forces II folder", ShowNewFolderButton = false, SelectedPath = folder.Text })
                    if (dialog.ShowDialog(this) == DialogResult.OK) folder.Text = dialog.SelectedPath;
            });
            AddLabel("Your original game and saves are kept.", 32, 421, 696, 24, 9, Color.Silver);
            status.SetBounds(32, 459, 696, 40); status.ForeColor = ForeColor;
            status.AccessibleName = "Installation status"; Controls.Add(status);
            progress.SetBounds(32, 509, 696, 5); progress.Visible = false; Controls.Add(progress);
            SetupButton(install, "Install", 32, 530, 225, delegate { InstallMod(); });
            SetupButton(play, "Play", 267, 530, 225, delegate {
                try { using (var process = installer.Play(folder.Text)) {} Remember(); } catch (Exception ex) { Error(ex); }
            });
            SetupButton(remove, "Uninstall", 502, 530, 225, delegate {
                if (MessageBox.Show(this, "Uninstall Rekindled? Your original game, saves and custom files will be kept.", "Uninstall Rekindled", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;
                string game = folder.Text;
                Work(delegate { int kept = installer.Uninstall(game); return kept == 0 ? "Rekindled uninstalled. Your original game and saves were kept." : "Rekindled uninstalled. Modified files and saves were kept."; });
            });
            Shown += delegate {
                var area = Screen.FromControl(this).WorkingArea;
                Size = new Size(Math.Min(Width, area.Width - 24), Math.Min(Height, area.Height - 24));
                ActiveControl = play.Enabled ? play : install.Enabled ? install : browse;
            };
            FormClosing += delegate(object sender, FormClosingEventArgs e) { if (busy) { e.Cancel = true; status.Text = "Please wait for the current operation to finish."; } };
            string saved = null;
            try { if (File.Exists(preference)) saved = File.ReadAllText(preference).Trim(); } catch (IOException) {} catch (UnauthorizedAccessException) {}
            if (!String.IsNullOrEmpty(saved)) {
                try { Installer.ValidateGame(saved); }
                catch (Exception) { saved = null; }
            }
            folder.Text = saved ?? FindGame() ?? "";
            RefreshState();
        }

        void AddLabel(string text, int x, int y, int w, int h, float size, Color color, bool display = false)
        {
            Controls.Add(new Label { Text = text, Left = x, Top = y, Width = w, Height = h, ForeColor = color,
                Font = display ? new Font(displayFonts.Families[0], size) : new Font("Segoe UI", size), AutoEllipsis = true });
        }
        void SetupButton(Button button, string text, int x, int y, int width, Action action)
        {
            button.Text = text; button.SetBounds(x, y, width, 41); button.FlatStyle = FlatStyle.Flat;
            button.Font = new Font(displayFonts.Families[0], 10);
            button.FlatAppearance.BorderColor = Color.FromArgb(81, 76, 62);
            button.BackColor = Color.FromArgb(36, 38, 42); button.ForeColor = ForeColor;
            button.Click += delegate { action(); }; Controls.Add(button);
        }
        void RefreshState()
        {
            if (busy) return;
            play.Enabled = remove.Enabled = install.Enabled = false;
            try {
                string game = Installer.ValidateGame(folder.Text);
                var state = installer.Installed(game);
                install.Enabled = true;
                play.Enabled = File.Exists(Path.Combine(game, "rpg", "openjkdf2-64.exe"));
                bool update = state != null && state.version != installer.Package.version;
                install.Text = state == null ? "Install" : update ? "Update" : "Repair";
                remove.Enabled = state != null;
                status.Text = update ? "A different version is installed. Select Update to install this release."
                    : play.Enabled ? "Rekindled is ready to play." : "Ready to install Rekindled.";
            } catch (Exception ex) { status.Text = ex.Message; }
            Button primary = play.Enabled && install.Text != "Update" ? play : install;
            foreach (Button button in new[] { install, play, remove }) {
                button.BackColor = button == primary ? gold : Color.FromArgb(36, 38, 42);
                button.ForeColor = button == primary ? Color.FromArgb(25, 23, 17) : ForeColor;
            }
        }
        void InstallMod()
        {
            string game = folder.Text;
            Work(delegate {
                installer.Install(game, delegate(int value, string message) { Invoke((Action)delegate { progress.Value = value; status.Text = message; }); });
                if (installer.RetainedBackup != null) return "Installed. Previous files were kept at " + installer.RetainedBackup;
                return "Rekindled is installed and ready to play.";
            });
        }
        void Remember()
        {
            // A read-only preferences folder must never turn a successful install into a failure.
            try { Directory.CreateDirectory(Path.GetDirectoryName(preference)); File.WriteAllText(preference, folder.Text); }
            catch (IOException) {} catch (UnauthorizedAccessException) {}
        }
        void Work(Func<string> operation)
        {
            busy = true; install.Enabled = play.Enabled = remove.Enabled = browse.Enabled = folder.Enabled = false;
            progress.Value = 0; progress.Visible = true; status.Text = "Checking your installation...";
            var worker = new BackgroundWorker();
            worker.DoWork += delegate(object sender, DoWorkEventArgs e) { e.Result = operation(); };
            worker.RunWorkerCompleted += delegate(object sender, RunWorkerCompletedEventArgs e) {
                busy = false; progress.Visible = false; browse.Enabled = folder.Enabled = true; RefreshState();
                if (e.Error != null) Error(e.Error); else { Remember(); status.Text = (string)e.Result; progress.Value = 100; }
                worker.Dispose();
            };
            worker.RunWorkerAsync();
        }
        void Error(Exception ex) { status.Text = ex.Message; MessageBox.Show(this, ex.Message, "Rekindled", MessageBoxButtons.OK, MessageBoxIcon.Warning); }

        static string FindGame()
        {
            var candidates = new List<string>();
            string steam = Convert.ToString(Registry.GetValue(@"HKEY_CURRENT_USER\Software\Valve\Steam", "SteamPath", null));
            if (!String.IsNullOrEmpty(steam)) {
                var libraries = new List<string> { steam };
                string file = Path.Combine(steam, "steamapps", "libraryfolders.vdf");
                try {
                    if (File.Exists(file)) foreach (Match match in Regex.Matches(File.ReadAllText(file), "\"path\"\\s+\"([^\"]+)\"")) libraries.Add(match.Groups[1].Value.Replace(@"\\", @"\"));
                } catch (IOException) {} catch (UnauthorizedAccessException) {}
                candidates.AddRange(libraries.Select(p => Path.Combine(p, "steamapps", "common", "Star Wars Jedi Knight")));
            }
            candidates.Add(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location));
            foreach (string path in candidates) { try { return Installer.ValidateGame(path); } catch (IOException) {} }
            return null;
        }
    }

    static class Program
    {
        [STAThread] static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            using (var mutex = new System.Threading.Mutex(false, @"Local\JediKnightRpgLauncher")) {
                bool held;
                try { held = mutex.WaitOne(0); } catch (System.Threading.AbandonedMutexException) { held = true; }
                if (!held) { MessageBox.Show("The launcher is already open.", "Rekindled"); return; }
                try {
                    var installer = new Installer(delegate { return Assembly.GetExecutingAssembly().GetManifestResourceStream("mod.zip"); });
                    Application.Run(new LauncherForm(installer));
                } catch (Exception ex) { MessageBox.Show(ex.Message, "Unable to open Rekindled", MessageBoxButtons.OK, MessageBoxIcon.Error); }
                finally { mutex.ReleaseMutex(); }
            }
        }
    }
}
