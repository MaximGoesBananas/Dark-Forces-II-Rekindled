using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;
using ModLauncher;

static class InstallerTests
{
    static int assertions;
    static void Check(bool value, string reason) { assertions++; if (!value) throw new Exception(reason); }
    static void Reject(Action operation, string reason)
    {
        bool failed = false;
        try { operation(); } catch (IOException) { failed = true; } catch (InvalidDataException) { failed = true; }
        Check(failed, reason);
    }
    static byte[] Zip(string version, string path, string content, bool corrupt, bool duplicate)
    {
        byte[] bytes = Encoding.UTF8.GetBytes(content);
        string hash;
        using (var sha = SHA256.Create()) hash = BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
        var manifest = new PackageManifest { format = 1, game = Installer.GameId, version = version, files = new[] { new PackageFile { path = path, size = bytes.Length, sha256 = corrupt ? new string('0', 64) : hash } } };
        using (var memory = new MemoryStream()) {
            using (var zip = new ZipArchive(memory, ZipArchiveMode.Create, true)) {
                using (var writer = new StreamWriter(zip.CreateEntry("manifest.json").Open())) writer.Write(new JavaScriptSerializer().Serialize(manifest));
                using (var stream = zip.CreateEntry(path).Open()) stream.Write(bytes, 0, bytes.Length);
                if (duplicate) using (var stream = zip.CreateEntry(path).Open()) stream.Write(bytes, 0, bytes.Length);
            }
            return memory.ToArray();
        }
    }
    static Installer Package(string version, string path, string content, bool corrupt = false, bool duplicate = false)
    {
        byte[] zip = Zip(version, path, content, corrupt, duplicate);
        return new Installer(delegate { return new MemoryStream(zip, false); });
    }
    static void Put(string root, string path, string content)
    {
        string full = Path.Combine(root, path); Directory.CreateDirectory(Path.GetDirectoryName(full)); File.WriteAllText(full, content);
    }
    [STAThread] static void Main(string[] args)
    {
        if (args.Length == 0) {
            File.WriteAllText("launch-probe.txt", Environment.CurrentDirectory + "\n" + Environment.GetEnvironmentVariable("OPENJKDF2_ROOT")); return;
        }
        if (args[0] == "--hold") { System.Threading.Thread.Sleep(10000); return; }
        string root = Path.GetFullPath(args[0]);
        Directory.CreateDirectory(root);
        foreach (string path in new[] { "Resource/Res1hi.gob", "Resource/Res2.gob", "Resource/jk_.cd", "Episode/JK1.gob", "player/Maxim/quicksave.jks" }) Put(root, path, "ORIGINAL");
        var one = Package("one", "art/test.bmp", "ONE");
        var two = Package("two", "art/test.bmp", "TWO");
        string installed = Path.Combine(root, "rpg/art/test.bmp");
        Reject(delegate { one.Install(Path.Combine(root, "missing"), null); }, "Reject missing game");
        foreach (string path in new[] { "../escape", "/escape", "C:/escape", "art\\escape", "NUL.txt", "a/./b", "a//b", "a /b", "COM1" })
            Reject(delegate { Package("bad", path, "BAD"); }, "Reject unsafe path " + path);
        one.Install(root, null);
        Check(File.ReadAllText(installed) == "ONE", "Fresh install");
        Check(one.Installed(root).version == "one", "Installed version");
        Put(root, "rpg/reports/location.png", "USER REPORT");
        Reject(delegate { Package("bad", "art/test.bmp", "BAD", true).Install(root, null); }, "Reject damaged payload");
        Reject(delegate { Package("bad", "art/test.bmp", "BAD", false, true).Install(root, null); }, "Reject duplicate payload");
        Reject(delegate { two.Install(root, delegate(int n, string s) { if (n == 90) throw new IOException("Interrupted update"); }); }, "Interrupted update");
        Check(File.ReadAllText(installed) == "ONE" && one.Installed(root).version == "one", "Failure preserves installed version");
        Check(!Directory.GetDirectories(root, ".rpg-stage-*").Any(), "Failed staging is cleaned");
        two.Install(root, null);
        Check(File.ReadAllText(installed) == "TWO" && two.Installed(root).version == "two", "Update");
        Check(File.ReadAllText(Path.Combine(root, "rpg/reports/location.png")) == "USER REPORT", "Update preserves reports");
        Check(!Directory.GetDirectories(root, ".rpg-previous-*").Any(), "Successful update removes verified backup");
        File.WriteAllText(installed, "CUSTOM");
        Reject(delegate { one.Install(root, null); }, "Modified owned file blocks overwrite");
        Check(two.Uninstall(root) == 1 && File.ReadAllText(installed) == "CUSTOM", "Uninstall preserves modified files");
        Check(File.Exists(Path.Combine(root, "rpg/reports/location.png")), "Uninstall preserves reports");
        Reject(delegate { one.Install(root, null); }, "Conflicting manual install preserved");
        File.WriteAllText(installed, "ONE");
        one.Install(root, null);
        Check(one.Installed(root).version == "one", "Adopt matching manual installation");
        Put(root, "rpg/custom.txt", "KEEP");
        Reject(delegate { Package("three", "custom.txt", "NEW").Install(root, null); }, "Custom file collision");
        var changed = Package("three", "new.txt", "NEW");
        changed.Install(root, null);
        Check(!File.Exists(installed), "Update removes obsolete owned file");
        Check(changed.Uninstall(root) == 0 && !File.Exists(Path.Combine(root, "rpg/new.txt")), "Clean uninstall");
        Check(File.ReadAllText(Path.Combine(root, "rpg/custom.txt")) == "KEEP", "Unowned file retained");
        foreach (string path in new[] { "Resource/Res1hi.gob", "Resource/Res2.gob", "Resource/jk_.cd", "Episode/JK1.gob", "player/Maxim/quicksave.jks" })
            Check(File.ReadAllText(Path.Combine(root, path)) == "ORIGINAL", "Original untouched: " + path);
        Reject(delegate { changed.Uninstall(root); }, "Unmanaged uninstall refuses");
        string probe = Path.Combine(root, "rpg/openjkdf2-64.exe");
        File.Copy(System.Reflection.Assembly.GetExecutingAssembly().Location, probe);
        using (var launched = one.Play(root)) { Check(launched.WaitForExit(5000) && launched.ExitCode == 0, "Play starts executable"); }
        Check(File.ReadAllText(Path.Combine(root, "launch-probe.txt")) == root + "\n" + root, "Play uses correct working directory and data root");
        using (var running = Process.Start(new ProcessStartInfo(probe, "--hold") { UseShellExecute = false, CreateNoWindow = true })) {
            try {
                Reject(delegate { one.Install(root, null); }, "Running game blocks install");
                Reject(delegate { one.Uninstall(root); }, "Running game blocks uninstall");
            } finally { running.Kill(); running.WaitForExit(); }
        }
        if (args.Length > 1) {
            var assembly = System.Reflection.Assembly.LoadFile(Path.GetFullPath(args[1]));
            var release = new Installer(delegate { return assembly.GetManifestResourceStream("mod.zip"); });
            string full = Path.Combine(root, "Release game");
            foreach (string path in new[] { "Resource/Res1hi.gob", "Resource/Res2.gob", "Resource/jk_.cd", "Episode/JK1.gob", "player/quicksave.jks" }) Put(full, path, "ORIGINAL");
            release.Install(full, null);
            foreach (var file in release.Package.files)
                Check(Installer.Hash(Path.Combine(full, "rpg", file.path)) == file.sha256, "Embedded release hash: " + file.path);
            string repair = Path.Combine(full, "rpg/art/upgrades.bmp");
            File.Delete(repair);
            release.Install(full, null);
            Check(File.Exists(repair), "Actual release repair");
            Check(release.Uninstall(full) == 0 && !Directory.Exists(Path.Combine(full, "rpg")), "Actual release uninstall");
            Check(File.ReadAllText(Path.Combine(full, "player/quicksave.jks")) == "ORIGINAL", "Actual release retains save");
        }
        Console.WriteLine("Installer: " + assertions + " assertions passed.");
    }
}
