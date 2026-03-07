param(
  [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$root = "Q:\Code\AI\GroupProject"
$docker = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
$supabase = "C:\Users\sakulal\AppData\Local\supabase\supabase.exe"

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

Set-Location $root
$env:PATH = "$env:PATH;C:\Program Files\Docker\Docker\resources\bin"

Step "Starting Supabase"
& $supabase start | Out-Host

Step "Starting Docker app services"
$composeArgs = @("compose", "up")
if ($Rebuild) { $composeArgs += "--build" }
$composeArgs += @("-d", "backend", "frontend")
& $docker @composeArgs | Out-Host

Step "Waiting for backend health"
$healthUrl = "http://127.0.0.1:8010/health"
$ok = $false
for ($i=0; $i -lt 30; $i++) {
  try {
    $r = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 5
    if ($r.status -eq "ok") { $ok = $true; break }
  } catch {}
  Start-Sleep -Seconds 2
}
if (-not $ok) { throw "Backend health check failed at $healthUrl" }
Write-Host "Backend healthy at $healthUrl" -ForegroundColor Green

Step "Baseline DB counts"
$baseline = & $docker exec supabase_db_Flux-Team-8 psql -U postgres -d postgres -t -A -c "SELECT (SELECT count(*) FROM public.goals), (SELECT count(*) FROM public.milestones), (SELECT count(*) FROM public.tasks), (SELECT count(*) FROM public.conversations);"
$parts = ($baseline | Select-Object -First 1).Trim().Split("|")
$g0=[int]$parts[0]; $m0=[int]$parts[1]; $t0=[int]$parts[2]; $c0=[int]$parts[3]
Write-Host "Before -> goals=$g0 milestones=$m0 tasks=$t0 conversations=$c0"

Step "Run goal planner flow via dockerized backend"
$base = "http://127.0.0.1:8010/orchestrator/message"
$user = "a1000000-0000-0000-0000-000000000001"

$s1 = Invoke-RestMethod -Uri $base -Method Post -ContentType "application/json" -Body (@{ user_id=$user; message="I want to lose weight for my wedding" } | ConvertTo-Json)
$cid = $s1.conversation_id

Invoke-RestMethod -Uri $base -Method Post -ContentType "application/json" -Body (@{ conversation_id=$cid; message="March 15th" } | ConvertTo-Json) | Out-Null
Invoke-RestMethod -Uri $base -Method Post -ContentType "application/json" -Body (@{ conversation_id=$cid; message="85 kg" } | ConvertTo-Json) | Out-Null
Invoke-RestMethod -Uri $base -Method Post -ContentType "application/json" -Body (@{ conversation_id=$cid; message="75 kg" } | ConvertTo-Json) | Out-Null
Invoke-RestMethod -Uri $base -Method Post -ContentType "application/json" -Body (@{ conversation_id=$cid; message="Gym and healthy diet" } | ConvertTo-Json) | Out-Null
$s6 = Invoke-RestMethod -Uri $base -Method Post -ContentType "application/json" -Body (@{ conversation_id=$cid; message="Looks good!" } | ConvertTo-Json)
$goalId = $s6.goal_id
Write-Host "Created goal_id=$goalId" -ForegroundColor Green

Step "Post-run DB counts"
$after = & $docker exec supabase_db_Flux-Team-8 psql -U postgres -d postgres -t -A -c "SELECT (SELECT count(*) FROM public.goals), (SELECT count(*) FROM public.milestones), (SELECT count(*) FROM public.tasks), (SELECT count(*) FROM public.conversations);"
$parts2 = ($after | Select-Object -First 1).Trim().Split("|")
$g1=[int]$parts2[0]; $m1=[int]$parts2[1]; $t1=[int]$parts2[2]; $c1=[int]$parts2[3]
Write-Host "After  -> goals=$g1 milestones=$m1 tasks=$t1 conversations=$c1"
Write-Host "Delta  -> goals=$(($g1-$g0)) milestones=$(($m1-$m0)) tasks=$(($t1-$t0)) conversations=$(($c1-$c0))" -ForegroundColor Yellow

if ($goalId) {
  $child = & $docker exec supabase_db_Flux-Team-8 psql -U postgres -d postgres -t -A -c "SELECT (SELECT count(*) FROM public.milestones WHERE goal_id = '$goalId'), (SELECT count(*) FROM public.tasks WHERE goal_id = '$goalId');"
  $cp = ($child | Select-Object -First 1).Trim().Split("|")
  Write-Host "Goal children -> milestones=$($cp[0]) tasks=$($cp[1])"
}

Step "Container status"
& $docker compose ps | Out-Host

Write-Host "`nTry now:" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173"
Write-Host "Backend:  http://localhost:8010/health"
Write-Host "Mode:     http://localhost:8010/orchestrator/mode"
Write-Host "Supabase: http://127.0.0.1:54323"
