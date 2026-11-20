import SwiftUI
import UIKit

enum StabilisStyle {
    static let paper = Color(light: 0xF7F6ED, dark: 0x192722)
    static let card = Color(light: 0xFFFEFA, dark: 0x22372E)
    static let ink = Color(light: 0x162B24, dark: 0xF7F6ED)
    static let secondary = Color(light: 0x4E6157, dark: 0xC4D5C9)
    static let rule = Color(light: 0xD4D9CF, dark: 0x455D50)
    static let accent = Color(light: 0x26523C, dark: 0xE2C875)
    static let warning = Color(light: 0x883F27, dark: 0xF8A88C)
    static let accentText = Color(light: 0xFFFFFF, dark: 0x162B24)
    static let brass = Color(red: 0.84, green: 0.73, blue: 0.38)
}

private extension Color {
    init(light: UInt32, dark: UInt32) {
        self.init(uiColor: UIColor { traits in
            let hex = traits.userInterfaceStyle == .dark ? dark : light
            return UIColor(red: CGFloat((hex >> 16) & 255) / 255,
                           green: CGFloat((hex >> 8) & 255) / 255,
                           blue: CGFloat(hex & 255) / 255, alpha: 1)
        })
    }
}

struct StabilisCard<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(17)
            .background(StabilisStyle.card, in: RoundedRectangle(cornerRadius: 14))
            .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(StabilisStyle.rule))
    }
}

struct StabilisButtonStyle: ButtonStyle {
    var primary = true

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.body.weight(.semibold))
            .multilineTextAlignment(.center)
            .frame(maxWidth: .infinity, minHeight: 46)
            .padding(.horizontal, 12)
            .padding(.vertical, 3)
            .foregroundStyle(primary ? StabilisStyle.accentText : StabilisStyle.accent)
            .background(primary ? StabilisStyle.accent : StabilisStyle.card, in: RoundedRectangle(cornerRadius: 9))
            .overlay(RoundedRectangle(cornerRadius: 9).strokeBorder(primary ? Color.clear : StabilisStyle.rule))
            .opacity(configuration.isPressed ? 0.75 : 1)
    }
}

struct WorkspaceMessage: View {
    let text: String
    var isError: Bool = false

    var body: some View {
        Label {
            Text(verbatim: text)
        } icon: {
            Image(systemName: isError ? "exclamationmark.circle" : "info.circle")
                .accessibilityHidden(true)
        }
        .font(.subheadline)
        .foregroundStyle(isError ? StabilisStyle.warning : StabilisStyle.secondary)
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
    }
}

struct StabilisMark: View {
    var body: some View {
        HStack(alignment: .bottom, spacing: 3) {
            ForEach([9.0, 15.0, 22.0], id: \.self) { height in
                RoundedRectangle(cornerRadius: 1)
                    .fill(StabilisStyle.brass)
                    .frame(width: 5, height: height)
            }
        }
        .frame(width: 42, height: 42)
        .background(Color(red: 0.086, green: 0.17, blue: 0.14), in: RoundedRectangle(cornerRadius: 8))
        .accessibilityHidden(true)
    }
}

enum WeekDate {
    static func iso(_ value: Date) -> String { formatter.string(from: value) }
    static func date(_ iso: String) -> Date? { formatter.date(from: String(iso.prefix(10))) }

    static func display(_ iso: String) -> String {
        date(iso)?.formatted(.dateTime.month(.abbreviated).day().year()) ?? iso
    }

    static func adding(_ days: Int, to iso: String) -> Date {
        let calendar = Calendar(identifier: .gregorian)
        let start = date(iso) ?? calendar.startOfDay(for: Date())
        return calendar.date(byAdding: .day, value: days, to: start) ?? start
    }

    private static var formatter: DateFormatter {
        let format = DateFormatter()
        format.calendar = Calendar(identifier: .gregorian)
        format.locale = Locale(identifier: "en_US_POSIX")
        format.dateFormat = "yyyy-MM-dd"
        return format
    }
}

func reviewMoney(_ value: Double?) -> String {
    guard let value, value.isFinite else { return "Needs data" }
    return value.formatted(.currency(code: "USD").precision(.fractionLength(0...2)).locale(Locale(identifier: "en_US")))
}

func reviewNumber(_ value: Double?) -> String {
    guard let value, value.isFinite else { return "Needs data" }
    return value.formatted(.number.precision(.fractionLength(0...2)))
}
