import SwiftUI

/// Wrapping row layout for pills and tags.
///
/// `HStack` would push everything onto one line and clip; `LazyVGrid` would
/// force equal-width columns, which looks wrong for chips of varying length.
struct FlowLayout: Layout {
    var spacing: CGFloat = 8
    var lineSpacing: CGFloat = 8
    var alignment: HorizontalAlignment = .leading

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? .infinity
        let rows = layout(subviews: subviews, maxWidth: maxWidth)

        let height = rows.reduce(into: CGFloat.zero) { total, row in
            total += row.height
        } + lineSpacing * CGFloat(max(0, rows.count - 1))

        let width = rows.map(\.width).max() ?? 0
        return CGSize(width: min(width, maxWidth), height: height)
    }

    func placeSubviews(
        in bounds: CGRect,
        proposal: ProposedViewSize,
        subviews: Subviews,
        cache: inout ()
    ) {
        let rows = layout(subviews: subviews, maxWidth: bounds.width)
        var y = bounds.minY

        for row in rows {
            // `HorizontalAlignment` is a struct, not an enum, so this compares
            // rather than pattern-matches.
            var x = bounds.minX
            if alignment == .center {
                x = bounds.minX + (bounds.width - row.width) / 2
            } else if alignment == .trailing {
                x = bounds.maxX - row.width
            }

            for item in row.items {
                subviews[item.index].place(
                    at: CGPoint(x: x, y: y + (row.height - item.size.height) / 2),
                    proposal: ProposedViewSize(item.size)
                )
                x += item.size.width + spacing
            }
            y += row.height + lineSpacing
        }
    }

    // MARK: Measurement

    private struct Item {
        let index: Int
        let size: CGSize
    }

    private struct Row {
        var items: [Item] = []
        var width: CGFloat = 0
        var height: CGFloat = 0
    }

    private func layout(subviews: Subviews, maxWidth: CGFloat) -> [Row] {
        var rows: [Row] = []
        var current = Row()

        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            let needed = current.items.isEmpty ? size.width : current.width + spacing + size.width

            if needed > maxWidth, !current.items.isEmpty {
                rows.append(current)
                current = Row()
                current.items = [Item(index: index, size: size)]
                current.width = size.width
                current.height = size.height
            } else {
                current.items.append(Item(index: index, size: size))
                current.width = needed
                current.height = max(current.height, size.height)
            }
        }

        if !current.items.isEmpty { rows.append(current) }
        return rows
    }
}

#Preview {
    ZStack {
        AuroraBackground()
        FlowLayout(spacing: 6) {
            ForEach(
                ["Internship", "Remote", "₹40,000 – ₹60,000", "Figma", "User research", "Bengaluru"],
                id: \.self
            ) { text in
                AttributePill(text: text)
            }
        }
        .padding()
    }
}
