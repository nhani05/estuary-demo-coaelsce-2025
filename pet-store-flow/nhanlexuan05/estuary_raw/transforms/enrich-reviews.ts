import { IDerivation, Document, SourceFromReviews } from 'flow/nhanlexuan05/estuary_raw/reviews-enriched.ts';

export class Derivation extends IDerivation {
    fromReviews(read: { doc: SourceFromReviews }): Document[] {
        const doc = read.doc;

        if (!doc.rating || doc.rating < 1 || doc.rating > 5) return [];

        const sentiment = doc.rating >= 4 ? 'positive'
                        : doc.rating <= 2 ? 'negative'
                        : 'neutral';

        return [{
            _meta: doc._meta,
            id: (doc as any)._id?.$oid ?? String((doc as any)._id),
            product_id: (doc as any).product_id ?? 'unknown',
            rating: doc.rating,
            sentiment,
            review_text: (doc as any).review_text ?? '',
            review_time: (doc as any).review_time
                ? new Date((doc as any).review_time).toISOString()
                : new Date().toISOString(),
            transformed_at: new Date().toISOString(),
        }];
    }
}
