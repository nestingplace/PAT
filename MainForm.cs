using System;
using System.IO;
using System.Windows.Forms;
namespace SAMPLE_IMPORT
{
    public partial class MainForm : Form
    {
        private string[] assignedFiles = new string[16];
        public MainForm()
        {
            InitializeComponent();
            InitDropdowns();
            InitSlots();
        }
        private void InitDropdowns()
        {
            for (int i = 1; i <= 4; i++)
            {
                programComboBox.Items.Add(i);
                bankComboBox.Items.Add(i);
            }
            programComboBox.SelectedIndex = 0;
            bankComboBox.SelectedIndex = 0;
        }
        private void InitSlots()
        {
            for (int i = 0; i < 16; i++)
            {
                Button btn = new Button { Text = $"Browse {i + 1}", Left = 10, Top = 50 + i * 30, Width = 80 };
                Label lbl = new Label { Text = "(None)", Left = 100, Top = 50 + i * 30, Width = 300 };
                int idx = i;
                btn.Click += (s, e) => BrowseFile(idx, lbl);
                Controls.Add(btn);
                Controls.Add(lbl);
            }
        }
        private void BrowseFile(int index, Label lbl)
        {
            using OpenFileDialog ofd = new OpenFileDialog();
            ofd.Filter = "Audio Files|*.wav;*.mp3;*.flac;*.ogg|All Files|*.*";
            if (ofd.ShowDialog() == DialogResult.OK)
            {
                assignedFiles[index] = ofd.FileName;
                lbl.Text = Path.GetFileName(ofd.FileName);
            }
        }
        private void RefreshSdButton_Click(object sender, EventArgs e)
        {
            sdCardComboBox.Items.Clear();

            foreach (var drive in DriveInfo.GetDrives())
            {
                if (drive.DriveType == DriveType.Removable && drive.IsReady)
                {
                    sdCardComboBox.Items.Add(drive.RootDirectory.FullName);
                }
            }

            if (sdCardComboBox.Items.Count > 0)
                sdCardComboBox.SelectedIndex = 0;
            else
                MessageBox.Show("No removable microSD cards detected.");
        }
        private void buildButton_Click(object sender, EventArgs e)
        {
            if (sdCardComboBox.SelectedItem == null)
            {
                MessageBox.Show("Please select an SD card first.");
                return;
            }
            string sdPath = sdCardComboBox.SelectedItem.ToString();
            int program = (int)programComboBox.SelectedItem;
            int bank = (int)bankComboBox.SelectedItem;
            string folderName = program.ToString("D2");  // "01" to "04"
            string programPath = Path.Combine(sdPath, folderName);
            Directory.CreateDirectory(programPath);  // Creates if not exists
            for (int i = 0; i < 16; i++)
            {
                string sourceFile = assignedFiles[i];
                if (!string.IsNullOrEmpty(sourceFile))
                {
                    int sampleNumber = ((bank - 1) * 16) + (i + 1);
                    string fileName = sampleNumber.ToString("D3") + ".mp3";
                    string destFile = Path.Combine(programPath, fileName);
                    if (File.Exists(destFile))
                    {
                        DialogResult result = MessageBox.Show(
                            $"Sample {fileName} already exists. Overwrite?",
                            "Confirm Overwrite", MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
                        if (result != DialogResult.Yes)
                            continue;
                    }
                    File.Copy(sourceFile, destFile, true);
                }
            }
            MessageBox.Show($"Samples uploaded to program {program} on SD card.");
        }
        private void DetectSDCard()
        {
            foreach (var drive in DriveInfo.GetDrives())
            {
                if (drive.DriveType == DriveType.Removable && drive.IsReady)
                {
                    Console.WriteLine($"Found SD card: {drive.Name}");
                }
            }
        }
        // optional: hook up FFmpeg call here
        private void ConvertAudio(string inputPath, string outputPath)
        {
            // use System.Diagnostics.Process to run ffmpeg
        }
    }
}
