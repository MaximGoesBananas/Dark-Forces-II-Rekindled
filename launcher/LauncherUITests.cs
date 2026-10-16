using System;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Windows.Forms;
using System.Web.Script.Serialization;
using ModLauncher;

static class LauncherUITests
{
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern int GetWindowLong(IntPtr h, int i);
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern int SetWindowLong(IntPtr h, int i, int v);
    static int checks;
    static void Check(bool ok, string message) { checks++; if (!ok) throw new Exception(message); }
    static T Field<T>(LauncherForm form, string name) { return (T)typeof(LauncherForm).GetField(name, BindingFlags.NonPublic | BindingFlags.Instance).GetValue(form); }
    static void Put(string root, string name, string text) { string path=Path.Combine(root,name); Directory.CreateDirectory(Path.GetDirectoryName(path)); File.WriteAllText(path,text); }
    static void Capture(LauncherForm form,string path) {
        Application.DoEvents();
        using(var image=new Bitmap(form.Width,form.Height)) { form.DrawToBitmap(image,new Rectangle(Point.Empty,form.Size)); image.Save(path); }
    }
    [STAThread] static void Main(string[] args)
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Installer installer;
        if (args[0].EndsWith(".zip")) installer=new Installer(()=>File.OpenRead(args[0]));
        else {
            var assembly=Assembly.LoadFile(Path.GetFullPath(args[0]));
            installer=new Installer(()=>assembly.GetManifestResourceStream("mod.zip"));
        }
        string output=Path.GetFullPath(args[1]); Directory.CreateDirectory(output);
        string root=Path.GetFullPath(args[2]);
        foreach(string name in new[]{"Resource/Res1hi.gob","Resource/Res2.gob","Resource/jk_.cd","Episode/JK1.gob"}) Put(root,name,"ORIGINAL");
        Check(Installer.ValidateGame(root)==root,"Game folder supports spaces and Unicode");
        Check(Installer.ValidateGame("\""+root+"\\\"")==root,"Pasted quoted path and trailing separator");
        Check(Installer.ValidateGame(root.Replace('\\','/'))==root,"Forward slash paths normalize");
        foreach(string invalid in new[]{".","C:relative","\\relative",root+"\0",Path.Combine(root,"Resource"),Path.Combine(root,"rpg")}) {
            bool rejected=false;
            try { Installer.ValidateGame(invalid); } catch(IOException) { rejected=true; }
            Check(rejected,"Reject invalid or incomplete game folder");
        }
        using(var form=new LauncherForm(installer)) {
            form.ShowInTaskbar=false;form.StartPosition=FormStartPosition.Manual;form.Location=new Point(-10000,-10000);
            SetWindowLong(form.Handle,-20,GetWindowLong(form.Handle,-20)|0x08000000);
            form.Show();Application.DoEvents();
            var folder=Field<TextBox>(form,"folder"); var install=Field<Button>(form,"install");
            var play=Field<Button>(form,"play"); var remove=Field<Button>(form,"remove"); var status=Field<Label>(form,"status");
            var progress=Field<ProgressBar>(form,"progress");
            Check(form.Controls.OfType<PictureBox>().Single().Image.Size==new Size(1280,400),"Full poster loaded without cropping");
            Check(form.Controls.OfType<Label>().Any(x=>x.Text=="STAR WARS JEDI KNIGHT: DARK FORCES II"),"Complete original title on one row");
            Check(form.Controls.OfType<Label>().Any(x=>x.Text=="REKINDLED"),"Distinct Rekindled heading");
            Check(!form.Controls.OfType<Label>().Any(x=>x.Text.StartsWith("Version ")),"Heading presents Rekindled without a version label");
            var heading=form.Controls.OfType<Label>().Single(x=>x.Text=="REKINDLED");
            Check(heading.Font.FontFamily.Name.StartsWith("Orbitron")&&play.Font.FontFamily.Name.StartsWith("Orbitron"),"Embedded display font used without system installation");
            Check(TextRenderer.MeasureText(heading.Text,heading.Font).Width<=heading.Width,"Display heading fits without truncation");
            Check(!form.Controls.OfType<Label>().Any(x=>x.Text.Contains("fan mod")||x.Text.Contains("Powered by")),"Credits stay outside the main actions");
            Check(!progress.Visible,"No empty progress bar before an operation");
            // Capture the actual detected local installation without changing it.
            Capture(form,Path.Combine(output,"launcher.png"));
            folder.Text=root;
            Check(install.Enabled&&install.Text=="Install"&&!play.Enabled&&!remove.Enabled,"Fresh install actions");
            Check(status.Text=="Ready to install Rekindled.","Fresh install guidance");
            Capture(form,Path.Combine(output,"fresh.png"));
            Put(root,"rpg/openjkdf2-64.exe","");folder.Text="";folder.Text=root;
            Check(play.Enabled&&!remove.Enabled&&status.Text=="Rekindled is ready to play.","Manual installation can play without contradictory guidance");
            Check(play.BackColor==Color.FromArgb(228,180,83),"Play is the primary installed action");
            var json=new JavaScriptSerializer();
            Put(root,"rpg/launcher-install.json",json.Serialize(installer.Package));folder.Text="";folder.Text=root;
            Check(install.Text=="Repair"&&remove.Enabled&&play.Enabled,"Managed installation actions");
            var prior=json.Deserialize<PackageManifest>(json.Serialize(installer.Package));prior.version="earlier";
            Put(root,"rpg/launcher-install.json",json.Serialize(prior));folder.Text="";folder.Text=root;
            Check(install.Text=="Update"&&install.BackColor==Color.FromArgb(228,180,83),"Different installed version offers update");
            folder.Text=Path.Combine(root,"missing");
            Check(!install.Enabled&&!play.Enabled&&!remove.Enabled,"Invalid folder disables file actions");
            folder.Text=root;
            // Deliberately short windows keep every control reachable through scrolling.
            form.Scale(new SizeF(2,2));form.Size=new Size(Math.Min(form.Width,1500),900);form.PerformLayout();
            Check(form.VerticalScroll.Visible,"Tall layout scrolls on a smaller desktop");
            form.ScrollControlIntoView(play);
            Check(play.Bottom<=form.ClientSize.Height,"Play remains reachable at a larger scale");
            Capture(form,Path.Combine(output,"scaled.png"));
        }
        Console.WriteLine("Launcher UI: "+checks+" checks passed.");
    }
}
