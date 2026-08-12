import Foundation
import Observation

/// Saved / applied / dismissed jobs.
///
/// Writes are optimistic: the card updates immediately and rolls back only if
/// the server rejects the change, which keeps swipe gestures feeling instant.
@MainActor
@Observable
final class SavedStore {
    private let api: APIClient

    private(set) var items: [SavedJob] = []
    private(set) var state: LoadState = .idle
    private(set) var dismissedIds: Set<Int> = []

    private var token: String?

    init(api: APIClient = .shared) {
        self.api = api
    }

    func configure(token: String?) {
        self.token = token
    }

    var savedIds: Set<Int> {
        Set(items.filter { $0.state != .dismissed }.map(\.id))
    }

    func isSaved(_ job: Job) -> Bool { savedIds.contains(job.id) }

    func state(for job: Job) -> SaveState? {
        items.first { $0.id == job.id }?.state
    }

    func load() async {
        guard let token else { return }
        if items.isEmpty { state = .loading }
        do {
            items = try await api.savedJobs(token: token)
            state = .loaded
        } catch {
            state = .failed((error as? APIError)?.errorDescription ?? error.localizedDescription)
        }
    }

    func toggleSave(_ job: Job) async {
        if isSaved(job) {
            await remove(job)
        } else {
            await set(job, to: .saved)
        }
    }

    func set(_ job: Job, to newState: SaveState) async {
        guard let token else { return }

        let previous = items
        // Optimistic write.
        if let index = items.firstIndex(where: { $0.id == job.id }) {
            items[index].state = newState
        } else {
            items.insert(SavedJob(job: job, state: newState, note: nil, createdAt: .now), at: 0)
        }
        if newState == .dismissed { dismissedIds.insert(job.id) }
        Haptics.play(newState == .dismissed ? .soft : .success)

        do {
            let saved = try await api.save(
                token: token,
                request: SaveRequest(jobId: job.id, state: newState, note: nil)
            )
            if let index = items.firstIndex(where: { $0.id == job.id }) {
                items[index] = saved
            }
        } catch {
            items = previous
            dismissedIds.remove(job.id)
            Haptics.play(.failure)
        }
    }

    func remove(_ job: Job) async {
        guard let token else { return }
        let previous = items
        items.removeAll { $0.id == job.id }
        Haptics.play(.light)

        do {
            try await api.unsave(token: token, jobId: job.id)
        } catch {
            items = previous
            Haptics.play(.failure)
        }
    }

    func restore(_ job: Job) {
        dismissedIds.remove(job.id)
    }
}
