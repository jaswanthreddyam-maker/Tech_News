import { Metadata } from 'next';
import { Container } from '@/components/layout/Container';
import FeedClient from './FeedClient';

export const metadata: Metadata = {
  title: 'For You - Tech News Today',
  description: 'Your personalized tech news feed.',
};

export default function FeedPage() {
  return (
    <Container className="py-12">
      <div className="mb-12">
        <h1 className="text-4xl font-bold font-mono tracking-tight mb-2">For You</h1>
        <p className="text-lg text-neutral-400">
          A personalized feed based on the topics and entities you follow.
        </p>
      </div>

      <FeedClient />
    </Container>
  );
}
