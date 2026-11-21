import CoreTransferable
import UniformTypeIdentifiers
import UIKit

struct PrintableReview: Transferable {
    let data: Data

    static var transferRepresentation: some TransferRepresentation {
        DataRepresentation(exportedContentType: .pdf) { $0.data }
    }

    @MainActor
    init(text: String) {
        let page = CGRect(x: 0, y: 0, width: 612, height: 792)
        let margin: CGFloat = 42
        let width = page.width - margin * 2
        let contentHeight = page.height - margin * 2
        let style = NSMutableParagraphStyle()
        style.paragraphSpacing = 2
        let attributes: [NSAttributedString.Key: Any] = [
            .font: UIFont.systemFont(ofSize: 10),
            .foregroundColor: UIColor.black,
            .paragraphStyle: style
        ]
        let document = UIGraphicsPDFRenderer(bounds: page)
        self.data = document.pdfData { context in
            context.beginPage()
            var y = margin
            for line in text.components(separatedBy: "\n") {
                let block = NSAttributedString(string: line.isEmpty ? " " : line, attributes: attributes)
                let height = ceil(block.boundingRect(
                    with: CGSize(width: width, height: .greatestFiniteMagnitude),
                    options: [.usesLineFragmentOrigin, .usesFontLeading], context: nil
                ).height)
                if y + height > margin + contentHeight {
                    context.beginPage()
                    y = margin
                }
                block.draw(with: CGRect(x: margin, y: y, width: width, height: height),
                           options: [.usesLineFragmentOrigin, .usesFontLeading], context: nil)
                y += height + 3
            }
        }
    }
}
