# Сборка блоков главной из шаблонов: подставляет адреса картинок и контакты.
# Запуск: powershell -File build.ps1 -Mode local|tilda
# local — картинки с временного сервера http://localhost:8765 (для проверки);
# tilda — картинки с сервера Тильды (адреса в urls.json рядом).
param([string]$Mode='local',[string]$Out="$env:TEMP\proelki_site")
[Threading.Thread]::CurrentThread.CurrentCulture=[Globalization.CultureInfo]::InvariantCulture
$here=Split-Path -Parent $MyInvocation.MyCommand.Path
$u=@{}
if($Mode -eq 'local'){ $b='http://localhost:8765'; $u=@{LOGO="$b/logo.png";HERODESK="$b/hero-desktop.jpg";HEROMOB="$b/hero-mobile.jpg";CITY="$b/gorod2.jpg"} }
else { $j=Get-Content "$here\urls.json" -Raw -Encoding UTF8 | ConvertFrom-Json; foreach($p in $j.PSObject.Properties){ $u[$p.Name]=$p.Value } }
$u.MAXURL='https://max.ru/u/f9LHodD0cOK6kULKP16FxmzpzVz3oNPdwg1uEciq9wvldICbrQREk6Yqk6s'
$u.TGURL='https://t.me/proelki03bot'
$u.TEL='+79025348081'
$u.TELTEXT='+7 902 534-80-81'
# огоньки на знаке
$pts=((Get-Content "$Out\lights.txt" -Raw -Encoding UTF8) -split '\|')[1].Trim().TrimEnd(';') -split ';'
$sel=@(); $i=0; foreach($p in $pts){ $xy=$p -split ','; $x=[double]$xy[0];$y=[double]$xy[1]
  $ok=$true; foreach($s in $sel){ if(([math]::Abs($s[0]-$x) -lt 4.5) -and ([math]::Abs($s[1]-$y) -lt 6.5)){$ok=$false;break} }
  if($ok){ $sel+=,@($x,$y) } }
$rng=New-Object Random 7; $lt=''
foreach($s in ($sel | Select-Object -First 34)){ $dl=-[math]::Round($rng.NextDouble()*2.6,2); $du=[math]::Round(2.0+$rng.NextDouble()*1.6,2)
  $lt+="<i class=`"tw`" style=`"left:$($s[0])%;top:$($s[1])%;animation-delay:${dl}s;animation-duration:${du}s`"></i>" }
$u.LIGHTS=$lt
foreach($f in 'hero-city','contacts'){
  $src="$here\$f.tpl.html"; if(-not (Test-Path $src)){continue}
  $t=Get-Content $src -Raw -Encoding UTF8
  foreach($k in $u.Keys){ $t=$t.Replace('{{'+$k+'}}',[string]$u[$k]) }
  [IO.File]::WriteAllText("$Out\$f.out.html",$t,(New-Object Text.UTF8Encoding $false))
  "$f -> $Out\$f.out.html ($($t.Length) знаков)"
}
