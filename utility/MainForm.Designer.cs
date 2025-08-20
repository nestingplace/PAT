namespace SAMPLE_IMPORT
{
    partial class MainForm
    {
        private System.ComponentModel.IContainer components = null;
        private System.Windows.Forms.ComboBox programComboBox;
        private System.Windows.Forms.ComboBox bankComboBox;
        private System.Windows.Forms.Button buildButton;
        ComboBox sdCardComboBox;
        Button refreshSdButton;
        private void InitializeComponent()
        {
            this.sdCardComboBox = new ComboBox { Left = 10, Top = 550, Width = 200 };
            this.refreshSdButton = new Button { Text = "Refresh SD Cards", Left = 220, Top = 550, Width = 140 };
            this.refreshSdButton.Click += RefreshSdButton_Click;
            this.Controls.Add(sdCardComboBox);
            this.Controls.Add(refreshSdButton);
            this.programComboBox = new System.Windows.Forms.ComboBox();
            this.bankComboBox = new System.Windows.Forms.ComboBox();
            this.buildButton = new System.Windows.Forms.Button();
            this.SuspendLayout();
            this.programComboBox.Location = new System.Drawing.Point(10, 10);
            this.bankComboBox.Location = new System.Drawing.Point(120, 10);
            this.buildButton.Location = new System.Drawing.Point(240, 10);
            this.buildButton.Text = "Build Program";
            this.buildButton.Click += new System.EventHandler(this.buildButton_Click);
            this.Controls.Add(this.programComboBox);
            this.Controls.Add(this.bankComboBox);
            this.Controls.Add(this.buildButton);
            this.ClientSize = new System.Drawing.Size(500, 600);
            this.Text = "Sample Import";
            this.ResumeLayout(false);
        }
    }
}
