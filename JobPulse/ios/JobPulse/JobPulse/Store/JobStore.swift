import Foundation
import Observation

enum LoadState: Equatable {
    case idle
    case loading
    case loaded
    case failed(String)

    var errorMessage: String? {
        if case .failed(let message) = self { return message }
        return nil
    }

    var isLoading: Bool { self == .loading }
}

/// Feed state for the Home and Incoming screens.
///
/// `filter` and `searchQuery` are plain stored properties rather than ones with
/// `didSet` observers: `@Observable` does not support property observers on
/// tracked properties, so the views call `filterChanged`/`searchChanged` from
/// `onChange` instead.
@MainActor
@Observable
final class JobStore {
    // Home
    private(set) var jobs: [Job] = []
    private(set) var feedState: LoadState = .idle
    private(set) var nextCursor: String?
    private(set) var isLoadingMore = false
    private(set) var total = 0

    // Incoming (grouped by company)
    private(set) var stacks: [CompanyStack] = []
    private(set) var stackState: LoadState = .idle

    // Detail cache, so revisiting a job from a stack is instant.
    private(set) var details: [Int: Job] = [:]

    var filter: FeedFilter = .all
    var searchQuery = ""

    @ObservationIgnored private let api: APIClient
    @ObservationIgnored private var lastInterests: [String] = []
    @ObservationIgnored private var reloadTask: Task<Void, Never>?
    @ObservationIgnored private var searchTask: Task<Void, Never>?

    init(api: APIClient = .shared) {
        self.api = api
    }

    // MARK: Change hooks

    func filterChanged(interests: [String]) {
        Haptics.play(.selection)
        reloadTask?.cancel()
        reloadTask = Task { [weak self] in
            await self?.load(interests: interests, force: true)
        }
    }

    /// Debounced so typing does not fire a request per keystroke.
    func searchChanged(interests: [String]) {
        searchTask?.cancel()
        searchTask = Task { [weak self] in
            try? await Task.sleep(for: .milliseconds(300))
            guard !Task.isCancelled else { return }
            await self?.load(interests: interests, force: true)
        }
    }

    // MARK: Feed

    func load(interests: [String], force: Bool = false) async {
        lastInterests = interests
        guard force || feedState != .loading else { return }

        if jobs.isEmpty { feedState = .loading }

        do {
            let response = try await api.feed(
                interests: interests,
                filter: filter,
                query: searchQuery.isEmpty ? nil : searchQuery
            )
            guard !Task.isCancelled else { return }
            jobs = response.items
            nextCursor = response.nextCursor
            total = response.total
            feedState = .loaded
        } catch is CancellationError {
            return
        } catch {
            feedState = .failed(message(for: error))
        }
    }

    func loadMoreIfNeeded(currentItem job: Job) async {
        // Prefetch when the user is three rows from the end.
        guard
            let cursor = nextCursor,
            !isLoadingMore,
            let index = jobs.firstIndex(where: { $0.id == job.id }),
            index >= jobs.count - 3
        else { return }

        isLoadingMore = true
        defer { isLoadingMore = false }

        do {
            let response = try await api.feed(
                interests: lastInterests,
                filter: filter,
                query: searchQuery.isEmpty ? nil : searchQuery,
                cursor: cursor
            )
            let known = Set(jobs.map(\.id))
            jobs.append(contentsOf: response.items.filter { !known.contains($0.id) })
            nextCursor = response.nextCursor
        } catch {
            nextCursor = nil  // stop trying rather than loop on a broken page
        }
    }

    // MARK: Stacks

    func loadStacks(interests: [String], force: Bool = false) async {
        guard force || stackState != .loading else { return }
        if stacks.isEmpty { stackState = .loading }

        do {
            stacks = try await api.stackedFeed(interests: interests).stacks
            stackState = .loaded
        } catch is CancellationError {
            return
        } catch {
            stackState = .failed(message(for: error))
        }
    }

    // MARK: Detail

    /// Returns the cached detail immediately when present.
    func detail(for id: Int) -> Job? { details[id] }

    @discardableResult
    func loadDetail(id: Int) async -> Job? {
        do {
            let job = try await api.job(id: id)
            details[id] = job
            return job
        } catch {
            return details[id]
        }
    }

    func refreshAll(interests: [String]) async {
        async let feed: Void = load(interests: interests, force: true)
        async let stacked: Void = loadStacks(interests: interests, force: true)
        _ = await (feed, stacked)
    }

    private func message(for error: Error) -> String {
        (error as? APIError)?.errorDescription ?? error.localizedDescription
    }
}
