# EXCEPTION: no GitHub account could be associated with this email.
# Deliberately comment-only, so no login is invented. Two effects, both intended:
#   * Contributor Attribution Check (contributor-check.yml) passes: it only tests
#     whether contributors/emails/<email> exists.
#   * release.py's _load_contributor_dir() skips files with no non-comment line, so
#     this email stays unmapped instead of being credited to a wrong account.
#
# konrad.mamsc@icloud.com  --  Konrad Czarski-Bonanaty
#   upstream commit c940027adef9a943d1c73911fb25cc11bb6101ca (PR #119806)
#
# Read-only evidence gathered 2026-10-07:
#   * repos/NousResearch/hermes-agent/commits/c940027adef9a943d1c73911fb25cc11bb6101ca
#       -> author.login is null
#   * search/commits?q=author-email:konrad.mamsc@icloud.com
#       -> 31 hits, author.login null in every one
#   * search/users?q=Konrad+Czarski-Bonanaty -> no match
#   * the commit's committer is a DIFFERENT person
#     (brooklyn! <brooklyn.bb.nicholson@gmail.com>, whose account OutThisLife opened
#     PR #119806), so crediting the committer would misattribute the work.
#
# Action if a login is ever supplied: run
#   python3 scripts/add_contributor.py konrad.mamsc@icloud.com <login> "<reference>"
# which replaces this file with the real mapping.
