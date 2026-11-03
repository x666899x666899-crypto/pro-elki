# Делает из знака на кремовом фоне прозрачный PNG и находит огоньки гирлянды (для мигания на сайте).
# Запуск: powershell -File logo-key.ps1 -Src знак.jpg -Dst знак.png
param([string]$Src,[string]$Dst,[int]$X=30,[int]$Y=160,[int]$W=964,[int]$H=700)
[Threading.Thread]::CurrentThread.CurrentCulture=[Globalization.CultureInfo]::InvariantCulture
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System; using System.Drawing; using System.Drawing.Imaging; using System.Collections.Generic; using System.Text; using System.Globalization;
public static class LogoKey {
  public static string Run(string src, string dst, int cx,int cy,int cw,int ch){
    CultureInfo inv=CultureInfo.InvariantCulture;
    Bitmap full=new Bitmap(src); Bitmap bmp=full.Clone(new Rectangle(cx,cy,cw,ch),PixelFormat.Format32bppArgb); full.Dispose();
    int w=bmp.Width,h=bmp.Height;
    BitmapData d=bmp.LockBits(new Rectangle(0,0,w,h),ImageLockMode.ReadWrite,PixelFormat.Format32bppArgb);
    int n=Math.Abs(d.Stride)*h; byte[] px=new byte[n]; System.Runtime.InteropServices.Marshal.Copy(d.Scan0,px,0,n);
    double br=253,bg=242,bb=224;
    List<double[]> cand=new List<double[]>();
    for(int y=0;y<h;y++){ for(int x=0;x<w;x++){ int i=y*d.Stride+x*4; double b=px[i],g=px[i+1],r=px[i+2];
      double dr=r-br,dg=g-bg,db=b-bb; double dist=Math.Sqrt(dr*dr+dg*dg+db*db);
      double a=(dist-16)/(64-16); if(a<0)a=0; if(a>1)a=1;
      if(a<0.02){px[i]=0;px[i+1]=0;px[i+2]=0;px[i+3]=0;continue;}
      double nr=br+(r-br)/a, ng=bg+(g-bg)/a, nb=bb+(b-bb)/a;
      nr=Math.Max(0,Math.Min(255,nr)); ng=Math.Max(0,Math.Min(255,ng)); nb=Math.Max(0,Math.Min(255,nb));
      px[i]=(byte)nb;px[i+1]=(byte)ng;px[i+2]=(byte)nr;px[i+3]=(byte)(a*255);
      if(a>0.95 && r>238 && g>195 && b<175 && (r-b)>70){ cand.Add(new double[]{x,y}); }
    } }
    System.Runtime.InteropServices.Marshal.Copy(px,0,d.Scan0,n); bmp.UnlockBits(d); bmp.Save(dst,ImageFormat.Png); bmp.Dispose();
    Dictionary<long,double[]> cells=new Dictionary<long,double[]>();
    foreach(double[] c in cand){ long key=((long)(c[0]/16))*10000+(long)(c[1]/16); double[] v; if(!cells.TryGetValue(key,out v)){v=new double[]{0,0,0};cells[key]=v;} v[0]+=c[0];v[1]+=c[1];v[2]+=1; }
    List<double[]> list=new List<double[]>(); foreach(var kv in cells){ if(kv.Value[2]>=8) list.Add(new double[]{kv.Value[0]/kv.Value[2],kv.Value[1]/kv.Value[2],kv.Value[2]}); }
    list.Sort((p,q)=>q[2].CompareTo(p[2]));
    StringBuilder sb=new StringBuilder();
    int cnt=0; foreach(double[] p in list){ if(cnt++>=50)break; sb.Append(Math.Round(p[0]/w*1000)/10.0).Append(",").Append(Math.Round(p[1]/h*1000)/10.0).Append(";"); }
    return w+"x"+h+" pts="+list.Count+"|"+sb.ToString();
  }
}
"@
[LogoKey]::Run($Src,$Dst,$X,$Y,$W,$H)
