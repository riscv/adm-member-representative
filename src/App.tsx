import { useState, useEffect } from 'react'
import { Search, Loader2, CheckCircle2, XCircle, Info, Clock, ExternalLink } from 'lucide-react'

interface MemberInfo {
  github_id: string;
  is_in_team: boolean;
  invitation_sent: boolean;
}

interface MemberData {
  [hash: string]: MemberInfo;
}

function App() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{
    found: boolean;
    info?: MemberInfo;
    searched: boolean;
  } | null>(null)
  const [members, setMembers] = useState<MemberData | null>(null)
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)

  useEffect(() => {
    // Fetch the membership data
    fetch(`${import.meta.env.BASE_URL}data.json`)
      .then(res => res.json())
      .then(data => {
        setMembers(data.members)
        setLastUpdated(data.last_updated)
      })
      .catch(err => console.error('Failed to load membership data:', err))
  }, [])

  const hashEmail = async (email: string) => {
    const msgUint8 = new TextEncoder().encode(email.toLowerCase().trim());
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return hashHex;
  }

  const maskGitHubId = (id: string) => {
    if (id.length <= 3) return id[0] + '***';
    return id.slice(0, 2) + '***' + id.slice(-1);
  }

  const maskEmail = (email: string) => {
    const [local, domain] = email.split('@');
    if (!domain) return email;
    const maskedLocal = local.length <= 2
      ? local[0] + '***'
      : local.slice(0, 2) + '***';
    const domainParts = domain.split('.');
    const tld = domainParts.length > 1 ? '.' + domainParts[domainParts.length - 1] : '';
    return maskedLocal + '@...' + tld;
  }

  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short',
    });
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return

    setLoading(true)
    setResult(null)

    // Simulate network delay for better UX
    await new Promise(resolve => setTimeout(resolve, 500))

    const hash = await hashEmail(email)

    if (members && members[hash] !== undefined) {
      setResult({
        found: true,
        info: members[hash],
        searched: true
      })
    } else {
      setResult({
        found: false,
        searched: true
      })
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-2xl text-center space-y-8">
        <div className="space-y-6">
          <a href="https://riscv.org" target="_blank" rel="noopener noreferrer">
            <img
              src={`${import.meta.env.BASE_URL}riscv.png`}
              alt="RISC-V Logo"
              className="h-20 mx-auto object-contain hover:opacity-80 transition-opacity"
            />
          </a>
          <h1 className="text-3xl font-bold text-berkeley-blue">
            Member Representative Search
          </h1>
          <p className="text-berkeley-blue/70 max-w-lg mx-auto">
            Verify your RISC-V Groups.io and GitHub Team membership.
          </p>
        </div>

        <form onSubmit={handleSearch} className="relative group">
          <div className="relative flex items-center">
            <Search className="absolute left-4 text-berkeley-blue/40 group-focus-within:text-berkeley-blue transition-colors" size={20} />
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value)
                setResult(null)
              }}
              placeholder="Enter your email address..."
              className="w-full pl-12 pr-32 py-4 bg-white border-2 border-berkeley-blue/10 rounded-full shadow-lg focus:shadow-xl focus:border-california-gold outline-none transition-all text-berkeley-blue text-lg"
              required
            />
            <button
              type="submit"
              disabled={loading}
              className="absolute right-2 bg-berkeley-blue hover:bg-berkeley-blue/90 text-white px-6 py-2 rounded-full font-semibold transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {loading ? <Loader2 className="animate-spin" size={20} /> : 'Search'}
            </button>
          </div>
          <p className="text-xs text-berkeley-blue/40 mt-2">
            Use the same email address associated with your RISC-V Groups.io account.
          </p>
        </form>

        <div className="min-h-[200px] flex flex-col items-center">
          {result && (
            <div className={`w-full p-8 rounded-2xl border-2 transition-all animate-in fade-in slide-in-from-top-4 duration-500 ${
              result.found ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
            }`}>
              {result.found && result.info ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-center gap-2 text-green-700 font-bold text-xl">
                    <CheckCircle2 size={28} />
                    <span>Member Found in Groups.io</span>
                  </div>

                  <div className="h-px bg-green-200 w-full my-4" />

                  <div className="space-y-4 text-left px-4">
                    <div className="flex items-center justify-between">
                      <span className="text-green-800 font-semibold">Is GitHub ID Set in Groups.io?</span>
                      <span className={`flex items-center gap-1 font-bold ${result.info.github_id ? 'text-green-600' : 'text-amber-600'}`}>
                        {result.info.github_id ? (
                          <>
                            <CheckCircle2 size={18} />
                            <a
                              href={`https://github.com/${result.info.github_id}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 hover:underline"
                            >
                              {maskGitHubId(result.info.github_id)}
                              <ExternalLink size={14} />
                            </a>
                          </>
                        ) : (
                          <><XCircle size={18} /> No</>
                        )}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-green-800 font-semibold">Is Part of the RISC-V GitHub Team?</span>
                      <span className={`flex items-center gap-1 font-bold ${result.info.is_in_team ? 'text-green-600' : 'text-amber-600'}`}>
                        {result.info.is_in_team ? (
                          <><CheckCircle2 size={18} /> Yes</>
                        ) : (
                          <><XCircle size={18} /> No</>
                        )}
                      </span>
                    </div>

                    {result.info.github_id && !result.info.is_in_team && (
                      <div className="flex items-center justify-between">
                        <span className="text-green-800 font-semibold">GitHub Invitation Sent?</span>
                        <span className={`flex items-center gap-1 font-bold ${result.info.invitation_sent ? 'text-blue-600' : 'text-amber-600'}`}>
                          {result.info.invitation_sent ? (
                            <><CheckCircle2 size={18} /> Yes</>
                          ) : (
                            <><XCircle size={18} /> No</>
                          )}
                        </span>
                      </div>
                    )}

                    {!result.info.github_id ? (
                      <div className="flex items-start gap-2 text-amber-700 bg-amber-50 p-3 rounded-lg border border-amber-200 text-sm mt-4">
                        <span className="mt-1"><Info size={18} /></span>
                        <div className="space-y-3">
                          <p>
                            Your <strong>GitHub Username</strong> (e.g., @johndoe) is not set in Groups.io. Please update your profile at{' '}
                            <a href="https://lists.riscv.org/g/main/editprofile" className="underline font-bold hover:text-amber-900">
                              lists.riscv.org
                            </a>.
                          </p>
                          <p>
                            Setting your GitHub username is <strong>extremely important</strong> as the RISC-V Specifications are developed using GitHub.
                            If you do not have a GitHub account, please <a href="https://docs.github.com/en/get-started/start-your-journey/creating-an-account-on-github" className="underline font-bold hover:text-amber-900" target="_blank" rel="noopener noreferrer">click here to create one</a>.
                          </p>
                          <p className="text-xs opacity-80 pt-1 border-t border-amber-200">
                            Note: We need your GitHub Username (found on your GitHub profile page), not your numeric ID.
                          </p>
                        </div>
                      </div>
                    ) : !result.info.is_in_team && result.info.invitation_sent ? (
                      <div className="flex items-start gap-2 text-blue-700 bg-blue-50 p-3 rounded-lg border border-blue-200 text-sm mt-4">
                        <span className="mt-1"><Info size={18} /></span>
                        <p>
                          A GitHub invitation has been sent to <strong>{maskGitHubId(result.info.github_id)}</strong> to join the RISC-V GitHub team.
                          <br /><br />
                          Please check your GitHub notifications or email for the invitation and accept it. If you haven't received it, check your spam folder or contact <a href="mailto:help@riscv.org" className="underline font-bold">help@riscv.org</a>.
                        </p>
                      </div>
                    ) : !result.info.is_in_team ? (
                      <div className="flex items-start gap-2 text-amber-700 bg-amber-50 p-3 rounded-lg border border-amber-200 text-sm mt-4">
                        <span className="mt-1"><Info size={18} /></span>
                        <p>
                          Your GitHub ID is set at the RISC-V Groups.io (lists.riscv.org), but you haven't been added to the RISC-V GitHub team yet.
                          <br /><br />
                          If you just updated your profile, please allow up to 3 hours for sync. Otherwise, if urgent or for any other issue, contact <a href="mailto:help@riscv.org" className="underline font-bold">help@riscv.org</a>.
                        </p>
                      </div>
                    ) : (
                      <div className="text-green-600 text-sm text-center font-medium mt-4 space-y-2">
                        <p>Everything looks good! Your membership and team access are active.</p>
                        <p className="text-green-500">
                          Your GitHub account{' '}
                          <a
                            href={`https://github.com/${result.info.github_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-bold underline hover:text-green-700"
                          >
                            @{maskGitHubId(result.info.github_id)}
                          </a>
                          {' '}is linked and part of the{' '}
                          <a
                            href="https://github.com/orgs/riscv/teams/risc-v-members"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-bold underline hover:text-green-700"
                          >
                            RISC-V Members
                          </a>
                          {' '}team.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-center gap-2 text-red-700 font-bold text-xl">
                    <XCircle size={28} />
                    <span>Account Not Found</span>
                  </div>
                  <p className="text-red-600">
                    We couldn't find an active RISC-V Groups.io account for <span className="font-bold">{maskEmail(email)}</span>.
                  </p>
                  <div className="h-px bg-red-200 w-full my-4" />
                  <div className="text-sm text-red-700 text-left space-y-3">
                    <p>
                      Groups.io is our source of truth to verify RISC-V Membership and Member Representatives. Please follow the steps below:
                    </p>
                    <ol className="list-decimal list-inside space-y-2 pl-1">
                      <li>
                        If you are <strong>not yet a RISC-V Member</strong>, visit{' '}
                        <a href="https://riscv.org/members/join/" className="underline font-bold">riscv.org/members/join/</a> to join.
                      </li>
                      <li>
                        If you are a <strong>member representative</strong> or hold an <strong>individual membership</strong>, send an email to{' '}
                        <a
                          href={`mailto:main+subscribe@lists.riscv.org?subject=Requested to be added to the RISC-V Group.io&body=Please add me (${email}) as part of lists.riscv.org. I came from the RISC-V Member Representative Search.`}
                          className="underline font-bold"
                        >
                          main+subscribe@lists.riscv.org
                        </a>{' '}
                        to request Groups.io access.
                      </li>
                      <li>
                        Once approved, update your profile (including your GitHub Username) at{' '}
                        <a href="https://lists.riscv.org/g/main/editprofile" className="underline font-bold">lists.riscv.org</a>.
                      </li>
                    </ol>
                    <p className="text-xs opacity-70 pt-2 border-t border-red-200">
                      Make sure you are searching with the same email address associated with your Groups.io account.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {!result && !loading && (
            <div className="text-berkeley-blue/40 flex flex-col items-center gap-4 mt-8">
              <div className="grid grid-cols-3 gap-8">
                <div className="flex flex-col items-center gap-2">
                  <div className="w-12 h-12 rounded-full bg-california-gold/10 flex items-center justify-center text-california-gold">
                    <CheckCircle2 size={24} />
                  </div>
                  <span className="text-xs font-semibold">Verify</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-12 h-12 rounded-full bg-berkeley-blue/10 flex items-center justify-center text-berkeley-blue">
                    <Search size={24} />
                  </div>
                  <span className="text-xs font-semibold">Search</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="w-12 h-12 rounded-full bg-california-gold/10 flex items-center justify-center text-california-gold">
                    <Info size={24} />
                  </div>
                  <span className="text-xs font-semibold">Update</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <footer className="fixed bottom-8 text-center">
        {lastUpdated && (
          <p className="text-berkeley-blue/30 text-xs flex items-center justify-center gap-1 mb-1">
            <Clock size={12} />
            Data last synced: {formatDate(lastUpdated)}
          </p>
        )}
        <p className="text-berkeley-blue/40 text-sm">
          © {new Date().getFullYear()} RISC-V International. All rights reserved.
        </p>
      </footer>
    </div>
  )
}

export default App
