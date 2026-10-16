using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;

namespace ModLauncher
{
    public sealed class PackageFile { public string path; public string sha256; public long size; }
    public sealed class PackageManifest
    {
        public int format;
        public string game;
        public string version;
        public string engineCommit;
        public PackageFile[] files;
    }

    public sealed class Installer
    {
        public const string GameId = "jedi-knight-rpg";
        public const string StateName = "launcher-install.json";
        readonly Func<Stream> openPackage;
        public readonly PackageManifest Package;
        public string RetainedBackup { get; private set; }
        static readonly JavaScriptSerializer Json = new JavaScriptSerializer();

        public Installer(Func<Stream> package)
        {
            openPackage = package;
            using (var stream = package())
            using (var zip = new ZipArchive(stream, ZipArchiveMode.Read))
            {
                var entry = zip.GetEntry("manifest.json");
                if (entry == null || entry.Length > 1024 * 1024) throw new InvalidDataException("Missing package information.");
                using (var reader = new StreamReader(entry.Open())) Package = ReadManifest(reader.ReadToEnd());
            }
        }

        static PackageManifest ReadManifest(string text)
        {
            var manifest = Json.Deserialize<PackageManifest>(text);
            if (manifest == null || manifest.format != 1 || manifest.game != GameId ||
                String.IsNullOrWhiteSpace(manifest.version) || manifest.files == null || manifest.files.Length == 0 || manifest.files.Length > 1000)
                throw new InvalidDataException("This is not a compatible Rekindled package.");
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            long total = 0;
            foreach (var file in manifest.files)
            {
                if (file == null) throw new InvalidDataException("Invalid package file information.");
                ValidateRelative(file.path);
                if (!seen.Add(file.path) || file.path.Equals(StateName, StringComparison.OrdinalIgnoreCase) ||
                    file.size < 0 || file.size > 256L * 1024 * 1024 || file.sha256 == null ||
                    file.sha256.Length != 64 || !file.sha256.All(Uri.IsHexDigit))
                    throw new InvalidDataException("Invalid package file information.");
                total += file.size;
                file.sha256 = file.sha256.ToLowerInvariant();
            }
            if (total > 512L * 1024 * 1024) throw new InvalidDataException("Package exceeds the supported size.");
            return manifest;
        }

        public static void ValidateRelative(string path)
        {
            if (String.IsNullOrEmpty(path) || path.Contains("\\") || Path.IsPathRooted(path) || path.Contains(":"))
                throw new InvalidDataException("Unsafe package path.");
            foreach (string part in path.Split('/'))
                if (part == "" || part == "." || part == ".." || part.EndsWith(".") || part.EndsWith(" ") ||
                    part.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 ||
                    System.Text.RegularExpressions.Regex.IsMatch(part, @"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)", System.Text.RegularExpressions.RegexOptions.IgnoreCase))
                    throw new InvalidDataException("Unsafe package path.");
        }

        static string Within(string root, string relative)
        {
            ValidateRelative(relative);
            string full = Path.GetFullPath(Path.Combine(root, relative.Replace('/', Path.DirectorySeparatorChar)));
            if (!full.StartsWith(Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("A package file points outside the mod folder.");
            return full;
        }

        public static string Hash(string path)
        {
            using (var sha = SHA256.Create())
            using (var file = File.OpenRead(path))
                return BitConverter.ToString(sha.ComputeHash(file)).Replace("-", "").ToLowerInvariant();
        }

        static void NoLinks(string path)
        {
            if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("The mod folder contains a link. Choose a normal folder so files can be managed safely.");
            if (Directory.Exists(path)) foreach (string child in Directory.GetFileSystemEntries(path)) NoLinks(child);
        }

        public static string ValidateGame(string folder)
        {
            if (String.IsNullOrWhiteSpace(folder)) throw new IOException("Choose your Jedi Knight game folder first.");
            string root;
            try {
                folder = folder.Trim().Trim('"');
                string drive = Path.GetPathRoot(folder);
                if (String.IsNullOrEmpty(drive) || drive.Length == 1 || drive.EndsWith(":"))
                    throw new IOException("Choose a complete game folder path using Browse.");
                root = Path.GetFullPath(folder);
                if (root.Length > Path.GetPathRoot(root).Length) root = root.TrimEnd(Path.DirectorySeparatorChar);
            } catch (ArgumentException) { throw new IOException("Choose a valid game folder using Browse."); }
              catch (NotSupportedException) { throw new IOException("Choose a valid game folder using Browse."); }
            string[] required = { "Resource/Res1hi.gob", "Resource/Res2.gob", "Resource/jk_.cd", "Episode/JK1.gob" };
            if (!Directory.Exists(root) || required.Any(p => !File.Exists(Path.Combine(root, p))))
                throw new IOException("Choose the Jedi Knight folder containing Resource and Episode. A full copy of Dark Forces II is required.");
            return root;
        }

        public static void RequireClosed()
        {
            var processes = Process.GetProcessesByName("openjkdf2-64");
            foreach (var process in processes) process.Dispose();
            if (processes.Length > 0)
                throw new IOException("Save your progress and close Jedi Knight before installing or removing Rekindled.");
        }

        public PackageManifest Installed(string game)
        {
            string root = Path.Combine(game, "rpg");
            if (!Directory.Exists(root)) return null;
            NoLinks(root);
            string state = Path.Combine(root, StateName);
            if (File.Exists(state) && new FileInfo(state).Length > 1024 * 1024) throw new InvalidDataException("Invalid installation record.");
            return File.Exists(state) ? ReadManifest(File.ReadAllText(state)) : null;
        }

        public void Install(string game, Action<int, string> progress)
        {
            RetainedBackup = null;
            game = ValidateGame(game);
            RequireClosed();
            string target = Path.Combine(game, "rpg");
            string stage = Path.Combine(game, ".rpg-stage-" + Guid.NewGuid().ToString("N"));
            string backup = Path.Combine(game, ".rpg-previous-" + Guid.NewGuid().ToString("N"));
            var old = Installed(game);
            var newPaths = new HashSet<string>(Package.files.Select(f => f.path), StringComparer.OrdinalIgnoreCase);
            var oldFiles = old == null ? new PackageFile[0] : old.files;
            var owned = new HashSet<string>(oldFiles.Select(f => f.path), StringComparer.OrdinalIgnoreCase);
            // A matching manual installation can be adopted; anything different is left alone.
            foreach (var file in oldFiles.Concat(Package.files.Where(f => !owned.Contains(f.path))))
            {
                string path = Within(target, file.path);
                if (!File.Exists(path)) continue;
                if (old != null && !owned.Contains(file.path))
                    throw new IOException("A custom file uses a name needed by this update: " + file.path);
                if (Hash(path) != file.sha256)
                    throw new IOException("An existing mod file was changed: " + file.path + ". Move or back it up before installing.");
            }
            bool movedOld = false, committed = false;
            try
            {
                Directory.CreateDirectory(stage);
                using (var stream = openPackage())
                using (var zip = new ZipArchive(stream, ZipArchiveMode.Read))
                {
                    var entries = zip.Entries.Where(e => e.FullName != "manifest.json").ToArray();
                    if (zip.Entries.Count != Package.files.Length + 1 || entries.Length != Package.files.Length || entries.Select(e => e.FullName).Distinct(StringComparer.OrdinalIgnoreCase).Count() != entries.Length)
                        throw new InvalidDataException("Unexpected or duplicate files in the package.");
                    for (int i = 0; i < Package.files.Length; i++)
                    {
                        var file = Package.files[i];
                        var entry = zip.GetEntry(file.path);
                        if (entry == null || entry.Length != file.size) throw new InvalidDataException("Incomplete package: " + file.path);
                        string path = Within(stage, file.path);
                        Directory.CreateDirectory(Path.GetDirectoryName(path));
                        using (var input = entry.Open())
                        using (var output = new FileStream(path, FileMode.CreateNew)) {
                            byte[] buffer = new byte[65536];
                            long remaining = file.size;
                            while (remaining > 0) {
                                int read = input.Read(buffer, 0, (int)Math.Min(buffer.Length, remaining));
                                if (read == 0) throw new InvalidDataException("Incomplete package: " + file.path);
                                output.Write(buffer, 0, read); remaining -= read;
                            }
                            if (input.ReadByte() != -1) throw new InvalidDataException("Oversized package entry: " + file.path);
                        }
                        if (Hash(path) != file.sha256) throw new InvalidDataException("Damaged download: " + file.path);
                        if (progress != null) progress((i + 1) * 85 / Package.files.Length, "Preparing Rekindled...");
                    }
                }
                if (Directory.Exists(target))
                {
                    NoLinks(target);
                    foreach (string source in Directory.GetFiles(target, "*", SearchOption.AllDirectories))
                    {
                        string rel = source.Substring(target.Length + 1).Replace('\\', '/');
                        if (rel == StateName || owned.Contains(rel) || newPaths.Contains(rel)) continue;
                        string dest = Within(stage, rel);
                        Directory.CreateDirectory(Path.GetDirectoryName(dest));
                        File.Copy(source, dest); // Reports and other user files survive updates.
                    }
                }
                File.WriteAllText(Path.Combine(stage, StateName), Json.Serialize(Package), new UTF8Encoding(false));
                if (progress != null) progress(90, "Installing Rekindled...");
                RequireClosed();
                if (Directory.Exists(target)) { Directory.Move(target, backup); movedOld = true; }
                try { Directory.Move(stage, target); committed = true; }
                catch { if (movedOld) Directory.Move(backup, target); movedOld = false; throw; }
                if (movedOld)
                {
                    try {
                        // Delete exact copies carried forward, or verified old owned files.
                        foreach (string path in Directory.GetFiles(backup, "*", SearchOption.AllDirectories))
                        {
                            string rel = path.Substring(backup.Length + 1).Replace('\\', '/');
                            string current = Within(target, rel);
                            var previous = oldFiles.FirstOrDefault(f => f.path.Equals(rel, StringComparison.OrdinalIgnoreCase));
                            bool copied = File.Exists(current) && Hash(path) == Hash(current);
                            if (copied || (previous != null && Hash(path) == previous.sha256) || rel == StateName) File.Delete(path);
                        }
                        RemoveEmpty(backup);
                    } catch (IOException) { RetainedBackup = backup; }
                      catch (UnauthorizedAccessException) { RetainedBackup = backup; }
                    if (Directory.Exists(backup)) RetainedBackup = backup;
                }
            }
            finally { if (!committed && Directory.Exists(stage)) DeleteStaging(stage, game); }
            if (progress != null) progress(100, "Installed. Ready to play.");
        }

        static void DeleteStaging(string path, string game)
        {
            if (Path.GetDirectoryName(Path.GetFullPath(path)) != Path.GetFullPath(game) || !Path.GetFileName(path).StartsWith(".rpg-stage-"))
                throw new IOException("Invalid staging directory.");
            NoLinks(path);
            foreach (string file in Directory.GetFiles(path, "*", SearchOption.AllDirectories)) File.Delete(file);
            RemoveEmpty(path);
        }

        static void RemoveEmpty(string path)
        {
            foreach (string child in Directory.GetDirectories(path)) RemoveEmpty(child);
            if (!Directory.EnumerateFileSystemEntries(path).Any()) Directory.Delete(path);
        }

        public int Uninstall(string game)
        {
            game = ValidateGame(game); RequireClosed();
            string root = Path.Combine(game, "rpg");
            var state = Installed(game);
            if (state == null) throw new IOException("This installation is not managed by the launcher. No files were removed.");
            int kept = 0;
            foreach (var file in state.files)
            {
                string path = Within(root, file.path);
                if (!File.Exists(path)) continue;
                if (Hash(path) == file.sha256) File.Delete(path); else kept++;
            }
            File.Delete(Path.Combine(root, StateName));
            RemoveEmpty(root);
            return kept;
        }

        public Process Play(string game)
        {
            game = ValidateGame(game);
            string exe = Path.Combine(game, "rpg", "openjkdf2-64.exe");
            if (!File.Exists(exe)) throw new IOException("Install Rekindled first.");
            var info = new ProcessStartInfo(exe) { WorkingDirectory = game, UseShellExecute = false };
            info.EnvironmentVariables["OPENJKDF2_ROOT"] = game;
            return Process.Start(info);
        }
    }
}
