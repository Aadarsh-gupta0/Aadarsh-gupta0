import Foundation

// MARK: - Configuration

enum APIConfig {
    /// Read from `JOBPULSE_API_BASE_URL` in Info.plist so the simulator, a
    /// device on your LAN and a deployed server differ only by build setting.
    static var baseURL: URL {
        if let raw = Bundle.main.object(forInfoDictionaryKey: "JOBPULSE_API_BASE_URL") as? String,
           let url = URL(string: raw.trimmingCharacters(in: .whitespaces)),
           url.scheme != nil {
            return url
        }
        return URL(string: "http://127.0.0.1:8000")!
    }

    static var apiKey: String? {
        let value = Bundle.main.object(forInfoDictionaryKey: "JOBPULSE_API_KEY") as? String
        return (value?.isEmpty ?? true) ? nil : value
    }

    static var appVersion: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "0.1"
    }
}

// MARK: - Errors

enum APIError: LocalizedError, Equatable {
    case badURL
    case transport(String)
    case http(status: Int, detail: String?)
    case decoding(String)
    case offline

    var errorDescription: String? {
        switch self {
        case .badURL:
            "That request could not be built."
        case .offline:
            "You appear to be offline."
        case .transport(let message):
            message
        case .http(let status, let detail):
            detail ?? "The server returned \(status)."
        case .decoding:
            "The server sent something this version of the app cannot read."
        }
    }

    /// Distinguishes "try again" from "this will not work until something changes".
    var isRetryable: Bool {
        switch self {
        case .offline, .transport: true
        case .http(let status, _): status >= 500 || status == 429
        case .badURL, .decoding: false
        }
    }
}

// MARK: - Client

/// Small async wrapper over `URLSession`. Deliberately not a protocol-per-method
/// abstraction: there is one backend, and previews inject sample data at the
/// store level instead.
actor APIClient {
    static let shared = APIClient()

    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init(session: URLSession? = nil) {
        if let session {
            self.session = session
        } else {
            let configuration = URLSessionConfiguration.default
            configuration.timeoutIntervalForRequest = 20
            configuration.waitsForConnectivity = true
            configuration.requestCachePolicy = .reloadRevalidatingCacheData
            self.session = URLSession(configuration: configuration)
        }

        decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom(Self.decodeDate)

        encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
    }

    // MARK: Feed

    func feed(
        interests: [String],
        filter: FeedFilter = .all,
        query: String? = nil,
        minScore: Double = 0.35,
        limit: Int = 25,
        cursor: String? = nil
    ) async throws -> FeedResponse {
        var items = [
            URLQueryItem(name: "filter", value: filter.rawValue),
            URLQueryItem(name: "minScore", value: String(minScore)),
            URLQueryItem(name: "limit", value: String(limit))
        ]
        items += interests.map { URLQueryItem(name: "interests", value: $0) }
        if let query, !query.isEmpty { items.append(URLQueryItem(name: "query", value: query)) }
        if let cursor { items.append(URLQueryItem(name: "cursor", value: cursor)) }

        return try await get("/v1/feed", query: items)
    }

    func stackedFeed(interests: [String], perCompany: Int = 5) async throws -> StackedFeedResponse {
        var items = [URLQueryItem(name: "perCompany", value: String(perCompany))]
        items += interests.map { URLQueryItem(name: "interests", value: $0) }
        return try await get("/v1/feed/stacked", query: items)
    }

    func job(id: Int) async throws -> Job {
        try await get("/v1/jobs/\(id)")
    }

    func company(slug: String) async throws -> CompanyDetail {
        try await get("/v1/companies/\(slug)")
    }

    func interests() async throws -> [Interest] {
        try await get("/v1/interests")
    }

    // MARK: Devices

    func register(_ registration: DeviceRegistration) async throws -> DeviceProfile {
        try await send("/v1/devices", method: "POST", body: registration)
    }

    func updateDevice(token: String, patch: DevicePatch) async throws -> DeviceProfile {
        try await send("/v1/devices/\(token)", method: "PATCH", body: patch)
    }

    func savedJobs(token: String) async throws -> [SavedJob] {
        try await get("/v1/devices/\(token)/saved")
    }

    func save(token: String, request: SaveRequest) async throws -> SavedJob {
        try await send("/v1/devices/\(token)/saved", method: "POST", body: request)
    }

    func unsave(token: String, jobId: Int) async throws {
        _ = try await raw("/v1/devices/\(token)/saved/\(jobId)", method: "DELETE", body: Data?.none)
    }

    // MARK: - Plumbing

    private func get<Response: Decodable>(
        _ path: String,
        query: [URLQueryItem] = []
    ) async throws -> Response {
        let data = try await raw(path, method: "GET", query: query, body: Data?.none)
        return try decode(data)
    }

    private func send<Body: Encodable, Response: Decodable>(
        _ path: String,
        method: String,
        body: Body
    ) async throws -> Response {
        let payload = try encoder.encode(body)
        let data = try await raw(path, method: method, body: payload)
        return try decode(data)
    }

    private func decode<Response: Decodable>(_ data: Data) throws -> Response {
        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw APIError.decoding(String(describing: error))
        }
    }

    @discardableResult
    private func raw(
        _ path: String,
        method: String,
        query: [URLQueryItem] = [],
        body: Data?
    ) async throws -> Data {
        guard
            var components = URLComponents(
                url: APIConfig.baseURL.appendingPathComponent(path),
                resolvingAgainstBaseURL: false
            )
        else { throw APIError.badURL }

        if !query.isEmpty { components.queryItems = query }
        guard let url = components.url else { throw APIError.badURL }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        if let key = APIConfig.apiKey {
            request.setValue(key, forHTTPHeaderField: "X-API-Key")
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch let error as URLError {
            throw error.code == .notConnectedToInternet
                ? APIError.offline
                : APIError.transport(error.localizedDescription)
        } catch {
            throw APIError.transport(error.localizedDescription)
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.transport("Unexpected response")
        }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.http(status: http.statusCode, detail: Self.detail(from: data))
        }
        return data
    }

    private static func detail(from data: Data) -> String? {
        guard
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else { return nil }
        if let detail = object["detail"] as? String { return detail }
        return nil
    }

    /// FastAPI emits ISO-8601 with microsecond precision, which the built-in
    /// `.iso8601` strategy rejects. Try the fractional formatter first, then
    /// the plain one, then a bare date.
    private static let fractionalFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static let plainFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    private static func decodeDate(_ decoder: Decoder) throws -> Date {
        let container = try decoder.singleValueContainer()
        let text = try container.decode(String.self)

        if let date = fractionalFormatter.date(from: text) { return date }
        if let date = plainFormatter.date(from: text) { return date }

        // Naive timestamps (no offset) come back from SQLite occasionally.
        let naive = DateFormatter()
        naive.locale = Locale(identifier: "en_US_POSIX")
        naive.timeZone = TimeZone(secondsFromGMT: 0)
        for format in ["yyyy-MM-dd'T'HH:mm:ss.SSSSSS", "yyyy-MM-dd'T'HH:mm:ss", "yyyy-MM-dd"] {
            naive.dateFormat = format
            if let date = naive.date(from: text) { return date }
        }

        throw DecodingError.dataCorruptedError(
            in: container,
            debugDescription: "Unrecognised date: \(text)"
        )
    }
}

// MARK: - Feed filter

/// Mirrors the chips in the reference design.
enum FeedFilter: String, CaseIterable, Identifiable, Sendable {
    case all
    case popular
    case new
    case internships
    case remote

    var id: String { rawValue }

    var label: String {
        switch self {
        case .all: "All"
        case .popular: "Popular"
        case .new: "New"
        case .internships: "Interns"
        case .remote: "Remote"
        }
    }
}
